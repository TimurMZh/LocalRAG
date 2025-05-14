import sys
import os
import json
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.reranker_service import RerankerRoberta, RerankerLaBSE
from services.milvus_vector_store import MilvusVectorStore
from config.settings import get_settings


def test_reranker():
    """
    Тестирование реранкера на примере поиска документов.
    """
    settings = get_settings()
    vector_store = MilvusVectorStore(embedding_model="roberta")
    reranker = RerankerLaBSE()

    # Тестовый запрос
    query = ("Қазақстан-2050 Стратегиясы еліміздің ұзақ мерзімді даму жоспарын айқындайды. Бұл стратегияның басты "
             "мақсаты – Қазақстанды әлемні")

    results = vector_store.search(query=query, top_k=50)

    if results.empty:
        print("Документы не найдены")
        return

    documents = [
        {
            "id": row["id"],
            "category": row["category"],
            "contents": row["contents"],
            "created_at": row["created_at"],
            "distance": row["distance"]
        }
        for _, row in results.iterrows()
    ]

    # Вывод исходных результатов
    print("\nИсходные результаты (топ-50):")
    for i, doc in enumerate(documents[:50]):
        print(f"{i + 1}. {doc['category']} (сходство: {doc['distance']:.4f})")
        print(f"   {doc['contents']}...")

    # Переранжирование результатов
    print("\nПереранжирование результатов...")
    reranked_docs = reranker(query, documents, top_k=50)

    # Вывод переранжированных результатов
    print("\nПереранжированные результаты (топ-50):")
    for i, doc in enumerate(reranked_docs):
        print(f"{i + 1}. {doc['category']} (сходство: {doc['distance']:.4f}, реранкинг: {doc['rerank_score']:.4f})")
        print(f"   {doc['contents']}...")


if __name__ == "__main__":
    test_reranker()