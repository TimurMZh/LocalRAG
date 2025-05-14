import torch
from abc import ABC, abstractmethod
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, util
import numpy as np


class Reranker(ABC):
    def __call__(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Метод для вызова реранкинга.

        Args:
            query: Поисковый запрос
            documents: Список документов для переранжирования
            top_k: Количество результатов для возврата

        Returns:
            Переранжированный список документов
        """
        return self.rerank(query, documents, top_k)

    @abstractmethod
    def _load_model(self):
        """Загрузка модели и токенизатора."""
        pass

    @abstractmethod
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5,
               batch_size: int = 8) -> List[Dict[str, Any]]:
        """
        Переранжирование результатов поиска.

        Args:
            query: Поисковый запрос
            documents: Список документов для переранжирования
            top_k: Количество результатов для возврата
            batch_size: Размер батча для обработки

        Returns:
            Переранжированный список документов
        """
        pass

class RerankerRoberta(Reranker):
    """
    Класс для переранжирования результатов поиска с помощью модели roberta-reranker-kaz.
    """
    def __init__(self, device: Optional[str] = None):
        """
        Инициализация реранкера.

        Args:
            model_name: Название модели для реранкинга
            device: Устройство для вычислений ('cuda', 'cpu' или None для автоматического выбора)
        """
        self.model_name = "nur-dev/roberta-reranker-kaz"
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.token = None
        self._load_model()

    def _load_model(self):
        """Загрузка модели и токенизатора."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.token)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, token=self.token)
        self.model.eval()
        self.model.to(self.device)

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5,
               batch_size: int = 8) -> List[Dict[str, Any]]:
        """
        Переранжирование результатов поиска.

        Args:
            query: Поисковый запрос
            documents: Список документов для переранжирования
            top_k: Количество результатов для возврата
            batch_size: Размер батча для обработки

        Returns:
            Переранжированный список документов
        """
        if not documents:
            return []

        # Подготовка пар запрос-документ для оценки
        pairs = [(query, doc["contents"]) for doc in documents]

        # Токенизация и получение оценок
        scores = []

        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i:i + batch_size]

            # Токенизация
            encoded = self.tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )

            # Перенос на нужное устройство
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            # Получение оценок
            with torch.no_grad():
                outputs = self.model(**encoded)
                batch_scores = outputs.logits.squeeze(-1).cpu().numpy()
                scores.extend(batch_scores)

        # Добавление оценок к документам и сортировка
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])

        # Сортировка по оценке reranking
        reranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # Возврат top-k результатов
        return reranked_docs[:top_k]

class RerankerLaBSE(Reranker):
    def __init__(self, device: Optional[str] = None):
        self.model_name = "sentence-transformers/LaBSE"
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self._load_model()
        
    def _load_model(self):
        self.model = SentenceTransformer('sentence-transformers/LaBSE')
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5, batch_size: int = 8) -> List[Dict[str, Any]]:
        if not documents:
            return []

        doc_texts = [doc["contents"] for doc in documents]
        query_emb = self.model.encode(query, convert_to_tensor=True)
        doc_embs = self.model.encode(doc_texts, convert_to_tensor=True, batch_size=batch_size)
        cos_scores = util.cos_sim(query_emb, doc_embs)[0]
        reranked = []

        for score, doc in zip(cos_scores.tolist(), documents):
            doc_copy = dict(doc)
            doc_copy["rerank_score"] = score
            reranked.append(doc_copy)

        reranked = sorted(reranked, key=lambda x: x["rerank_score"], reverse=True)

        return reranked[:top_k]