import json
import uuid
from datetime import datetime
from http import HTTPStatus
import os
import tempfile
from typing import Optional

import pandas as pd
from config.celery_config import celery_app
from database.event import Event
from database.repository import GenericRepository
from services.reranker_service import RerankerRoberta, RerankerLaBSE
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.responses import Response

from api.dependencies import db_session
from api.event_schema import EventSchema
from timescale_vector.client import uuid_from_time

from config.settings import get_settings
from utils.document_process import read_txt, read_docx, read_pdf, chunk_text
from services.llm_factory import LLMFactory
from pydantic import BaseModel, Field
from services.milvus_vector_store import MilvusVectorStore
from transformers import T5Tokenizer, T5ForConditionalGeneration
import sentencepiece

EMBEDDING_MODEL = "openai"  # Варианты: "roberta" или "openai"
ANSWER_MODEL = "t5"  # Варианты: "t5" или "openai"

"""
Event Submission Endpoint Module

This module defines the primary FastAPI endpoint for event ingestion.
It implements the initial handling of incoming events by:
1. Validating the incoming event data
2. Persisting the event to the database
3. Queuing an asynchronous processing task
4. Returning an acceptance response

The endpoint follows the "accept-and-delegate" pattern where:
- Events are immediately accepted if valid
- Processing is handled asynchronously via Celery
- A 202 Accepted response indicates successful queueing

This pattern ensures high availability and responsiveness of the API
while allowing for potentially long-running processing operations.
"""

router = APIRouter()


@router.post("/", dependencies=[])
def handle_event(
        data: EventSchema,
        session: Session = Depends(db_session),
) -> Response:
    """Handles incoming event submissions.

    This endpoint receives events, stores them in the database,
    and queues them for asynchronous processing. It implements
    a non-blocking pattern to ensure API responsiveness.

    Args:
        data: The event data, validated against EventSchema
        session: Database session injected by FastAPI dependency

    Returns:
        Response: 202 Accepted response with task ID

    Note:
        The endpoint returns immediately after queueing the task.
        Use the task ID in the response to check processing status.
    """
    # Store event in database
    repository = GenericRepository(
        session=session,
        model=Event,
    )
    event = Event(data=data.model_dump(mode="json"))
    repository.create(obj=event)

    # Queue processing task
    task_id = celery_app.send_task(
        "process_incoming_event",
        args=[str(event.id)],
    )

    # Return acceptance response
    return Response(
        content=json.dumps({"message": f"process_incoming_event started `{task_id}` "}),
        status_code=HTTPStatus.ACCEPTED,
    )


rag_router = APIRouter()


class QuestionRequest(BaseModel):
    question: str = Field(..., description="Вопрос для модели")
    model: str = Field(..., description="Модель")


class ResponseModel(BaseModel):
    response: str = Field(
        description="Текстовый ответ на заданный вопрос"
    )


class SearchRequest(BaseModel):
    query: str = Field(..., description="Поисковый запрос")
    model: str = Field(default="openai", description="Модель для поиска (openai или roberta)")


@rag_router.post("/ask")
def ask(request: QuestionRequest = Body(...)) -> Response:
    """
    Handles a question from the user and generates an answer using either T5 model or OpenAI.
    """
    try:

        if request.model == "t5":
            vector_store = MilvusVectorStore(embedding_model="roberta")
            df = vector_store.search(request.question, top_k=5)

            results = [
                {
                    "id": row["id"],
                    "category": row["category"],
                    "contents": row["contents"],
                    "created_at": row["created_at"],
                    "distance": row["distance"]
                }
                for _, row in df.iterrows()
            ]
            reranker = RerankerLaBSE()

            reranked_docs = reranker(request.question, results, top_k=50)

            context = " ".join([doc["contents"] for doc in reranked_docs])

            tokenizer = T5Tokenizer.from_pretrained("Kyrmasch/t5-kazakh-qa")
            model = T5ForConditionalGeneration.from_pretrained("Kyrmasch/t5-kazakh-qa")

            encoded = tokenizer.encode_plus(
                context, 
                request.question, 
                max_length=512,
                padding="max_length",
                truncation=True, 
                return_tensors="pt"
            )
            input_ids = encoded["input_ids"].to('cpu')
            attention_mask = encoded["attention_mask"].to('cpu')

            output = model.generate(
                input_ids=input_ids, 
                attention_mask=attention_mask, 
                max_length=128,
                early_stopping=True,
                num_beams=4,
                no_repeat_ngram_size=2
            )
            answer = ''.join([tokenizer.decode(ids, skip_special_tokens=True) for ids in output])
        else:  # openai
            vector_store = MilvusVectorStore(embedding_model=request.model)
            df = vector_store.search(request.question, top_k=25)

            results = [
                {
                    "id": row["id"],
                    "category": row["category"],
                    "contents": row["contents"],
                    "created_at": row["created_at"],
                    "distance": row["distance"]
                }
                for _, row in df.iterrows()
            ]
            reranker = RerankerLaBSE()

            reranked_docs = reranker(request.question, results, top_k=50)

            context = " ".join([doc["contents"] for doc in reranked_docs])

            llm = LLMFactory("openai")

            messages = [
                {"role": "system", "content": "Вы - помощник, который отвечает на вопросы на основе предоставленного контекста. "
                                              "Отвечать необходимо на казахском языке"},
                {"role": "user", "content": f"Контекст: {context}\n\nВопрос: {request.question}"}
            ]
            
            # Создаем модель ответа
            class AnswerModel(BaseModel):
                answer: str
                
            # Получаем ответ от OpenAI
            response, _ = llm.create_completion(AnswerModel, messages)
            answer = response.answer

        return Response(
            content=json.dumps({"answer": answer}, ensure_ascii=False),
            status_code=HTTPStatus.OK,
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )


@rag_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    model: str = Form(...)
):
    """
    Uploads a document (TXT, DOCX, PDF), extracts its text content,
    creates embeddings, and stores them in Milvus.
    """
    vector_store = MilvusVectorStore(embedding_model=model)
    ext = file.filename.split(".")[-1].lower()
    filename_without_ext = ".".join(file.filename.split(".")[:-1]) or file.filename
    content = await file.read()

    if ext == "txt":
        text = read_txt(content)
    elif ext == "docx":
        text = read_docx(content)
    elif ext == "pdf":
        text = read_pdf(content)
    elif ext == "json":
        text = content.decode("utf-8")  # or process as needed
    else:
        return {"error": f"Unsupported file type: {ext}"}

    chunks = chunk_text(text)
    records = []

    for chunk in chunks:
        embedding = vector_store.get_embedding(chunk)
        records.append({
            "id": str(uuid.uuid4()),
            "category": filename_without_ext,
            "created_at": datetime.utcnow().isoformat(),
            "contents": chunk,
            vector_store.vector_settings.table_name: embedding
        })

    df = pd.DataFrame(records)
    vector_store.insert(df)

    return {"message": f"Документ загружен '{file.filename}'"}


@rag_router.post("/documents/search", dependencies=[])
def document_search(request: SearchRequest) -> Response:
    """
    Performs a semantic search against the stored document chunks
    using a vector similarity search based on the user's query.
    """
    vector_store = MilvusVectorStore(embedding_model=request.model)
    if vector_store.is_connected:
        result = vector_store.search(query=request.query, top_k=50)

        if result.empty:
            return JSONResponse(status_code=200, content={"results": []})

        results = [
            {
                "id": row["id"],
                "category": row["category"],
                "contents": row["contents"],
                "created_at": row["created_at"],
                "distance": row["distance"]
            }
            for _, row in result.iterrows()
        ]
        reranker = RerankerLaBSE()

        reranked_docs = reranker(request.query, results, top_k=50)

        return JSONResponse(
                status_code=200,
                content={"results": reranked_docs}
            )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Подключение не установлено!"}
        )