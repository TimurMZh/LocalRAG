import os
import re
import sys
import numpy as np
from typing import List, Dict, Optional, Any, Tuple, Set
import logging
from functools import lru_cache
import time

from datasets import load_dataset
from rank_bm25 import BM25Okapi, BM25Plus
from tokenizer import KazakhTokenizer


class KazQADRetrievalError(Exception):
    """Базовое исключение для KazQADRetrieval"""
    pass


class NoPassagesError(KazQADRetrievalError):
    """Исключение, когда не найдено ни одного passage"""
    pass


class InvalidQueryError(KazQADRetrievalError):
    """Исключение для некорректных запросов"""
    pass


# Fix for Windows console encoding issues
if sys.platform == 'win32':
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Настройка логирования с решением проблемы Unicode
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output is now UTF-8 encoded
        logging.FileHandler('retrieval.log', mode='a', encoding='utf-8')  # File output is explicitly UTF-8
    ]
)
logger = logging.getLogger(__name__)


class KazQADRetrieval:
    # Синонимы для расширения запросов
    KAZAKH_SYNONYMS = {
        'қала': ['қалалар', 'қаласы', 'шаһар'],
        'тарих': ['тарихи', 'тарихта', 'тарихшы'],
        'астана': ['бас қала', 'елорда'],
        'мектеп': ['оқу орны', 'білім беру'],
        'университет': ['оқу орны', 'жоғары оқу орны'],
        'кітап': ['кітаптар', 'оқулық'],
        'әдебиет': ['шығарма', 'шығармалар'],
        'ел': ['мемлекет', 'отан', 'ұлт'],
        'жыл': ['жылдар', 'жылдық']
    }

    def __init__(
            self,
            dataset_name: str = 'issai/kazqad-retrieval',
            cache_dir: Optional[str] = None,
            top_k: int = 5,
            threshold: float = 0.1,  # Lowered threshold to get results
            bm25_variant: str = 'plus',
            use_stemming: bool = True
    ):
        """
        Инициализация системы retrieval с расширенными параметрами

        :param dataset_name: Название датасета
        :param cache_dir: Директория для кэширования
        :param top_k: Количество возвращаемых результатов по умолчанию
        :param threshold: Порог релевантности по умолчанию
        :param bm25_variant: Вариант BM25 ('classic' или 'plus')
        :param use_stemming: Использовать ли стемминг при токенизации
        """
        start_time = time.time()
        logger.info(f"Initializing KazQADRetrieval with dataset: {dataset_name}")

        self.top_k = top_k
        self.threshold = threshold
        self.use_stemming = use_stemming
        self.last_query_time = 0
        self.query_count = 0
        self.cache_hits = 0

        # Установка директории кэша
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(__file__),
                'dataset_cache'
            )
        os.makedirs(cache_dir, exist_ok=True)

        try:
            # Загрузка датасета
            self.dataset = load_dataset(
                dataset_name,
                cache_dir=cache_dir
            )
            logger.info(f"Dataset loaded successfully: {dataset_name}")

            # Подготовка passages
            self.passages = self._extract_passages()
            logger.info(f"Extracted {len(self.passages)} passages from dataset")

            # Токенизация passages
            self.tokenized_passages = [
                self._tokenize(passage) for passage in self.passages
            ]
            logger.info(f"Tokenized {len(self.tokenized_passages)} passages")

            # Создание BM25 индекса
            if bm25_variant.lower() == 'plus':
                self.bm25 = BM25Plus(self.tokenized_passages)
                logger.info("Using BM25Plus ranking algorithm")
            else:
                self.bm25 = BM25Okapi(self.tokenized_passages)
                logger.info("Using BM25Okapi ranking algorithm")

            # Создание обратного индекса для быстрого поиска
            self.inverted_index = self._build_inverted_index()

            init_time = time.time() - start_time
            logger.info(f"Initialization completed in {init_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise

    def _extract_passages(self) -> List[str]:
        """
        Извлечение passages из датасета с расширенной фильтрацией
        """
        passages = []
        passage_ids = set()  # Для отслеживания уникальных passages

        try:
            # Проверяем разные сплиты
            for split in ['train', 'validation', 'test']:
                if split in self.dataset:
                    logger.info(f"Processing '{split}' split")

                    for example in self.dataset[split]:
                        # Извлекаем положительные passages
                        if 'positive_passages' in example:
                            for passage in example['positive_passages']:
                                if 'text' in passage and passage['text'] not in passage_ids:
                                    passages.append(passage['text'])
                                    passage_ids.add(passage['text'])

                        # Извлекаем отрицательные passages
                        if 'negative_passages' in example:
                            for passage in example['negative_passages']:
                                if 'text' in passage and passage['text'] not in passage_ids:
                                    passages.append(passage['text'])
                                    passage_ids.add(passage['text'])

            # Проверка на наличие passages
            if not passages:
                logger.error("No passages extracted from dataset")
                raise NoPassagesError("Не удалось извлечь passages из датасета")

            logger.info(f"Extracted {len(passages)} unique passages")

            # Очистка и фильтрация passages
            cleaned = self._clean_passages(passages)
            logger.info(f"After cleaning: {len(cleaned)} passages")

            return cleaned

        except Exception as e:
            logger.error(f"Error extracting passages: {str(e)}")
            raise

    def _clean_passages(self, passages: List[str]) -> List[str]:
        """
        Расширенная очистка и фильтрация passages
        """
        cleaned_passages = []
        too_short = 0
        no_kazakh = 0
        too_long = 0

        for passage in passages:
            try:
                # Удаление лишних пробелов и нормализация
                cleaned = re.sub(r'\s+', ' ', passage).strip()

                # Удаление HTML-тегов, если они есть
                cleaned = re.sub(r'<[^>]+>', '', cleaned)

                # Удаление слишком коротких пассажей
                if len(cleaned) < 20:
                    too_short += 1
                    continue

                # Проверка на казахские символы
                kazakh_chars = sum(1 for c in cleaned if c in 'әіңғүұқөһ')
                if kazakh_chars < 3 and len(cleaned) > 50:
                    no_kazakh += 1
                    continue

                # Обрезка слишком длинных passages
                if len(cleaned) > 1000:
                    cleaned = cleaned[:1000]
                    too_long += 1

                cleaned_passages.append(cleaned)

            except Exception as e:
                logger.warning(f"Error cleaning passage: {str(e)}")
                # Пропускаем проблемные passages, но продолжаем обработку

        logger.info(f"Cleaned passages statistics: "
                    f"{too_short} too short, "
                    f"{no_kazakh} without Kazakh chars, "
                    f"{too_long} truncated due to length")

        return cleaned_passages

    def _tokenize(self, text: str) -> List[str]:
        """
        Токенизация с использованием KazakhTokenizer
        """
        try:
            return KazakhTokenizer.tokenize(text, apply_stemming=self.use_stemming)
        except Exception as e:
            logger.warning(f"Tokenization error: {str(e)}")
            # В случае ошибки возвращаем простую токенизацию
            return text.lower().split()

    def _build_inverted_index(self) -> Dict[str, Set[int]]:
        """
        Создание обратного индекса для быстрого поиска
        """
        inverted_index = {}

        for idx, tokens in enumerate(self.tokenized_passages):
            for token in set(tokens):  # Используем set для уникальности
                if token not in inverted_index:
                    inverted_index[token] = set()
                inverted_index[token].add(idx)

        logger.info(f"Built inverted index with {len(inverted_index)} unique tokens")
        return inverted_index

    def _expand_query(self, tokens: List[str]) -> List[str]:
        """
        Расширение запроса синонимами
        """
        expanded = tokens.copy()
        for token in tokens:
            if token in self.KAZAKH_SYNONYMS:
                expanded.extend(self.KAZAKH_SYNONYMS[token])
        return expanded

    def _filter_by_tokens(self, query_tokens: List[str]) -> List[int]:
        """
        Быстрая предварительная фильтрация по токенам с использованием обратного индекса
        """
        if not query_tokens:
            return []

        # Получаем все документы, содержащие хотя бы один токен запроса
        candidate_docs = set()
        for token in query_tokens:
            if token in self.inverted_index:
                if not candidate_docs:  # Первый токен
                    candidate_docs = self.inverted_index[token].copy()
                else:
                    candidate_docs.update(self.inverted_index[token])

        return list(candidate_docs)

    @lru_cache(maxsize=256)
    def retrieve(
            self,
            query: str,
            top_k: Optional[int] = None,
            threshold: Optional[float] = None,
            expand_query: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Расширенный retrieval passages по запросу с кэшированием

        :param query: Текстовый запрос
        :param top_k: Количество возвращаемых результатов
        :param threshold: Порог релевантности
        :param expand_query: Расширять ли запрос синонимами
        :return: Список найденных passages с их scores
        """
        # Измерение времени выполнения
        start_time = time.time()
        self.query_count += 1

        # Использование значений по умолчанию, если не указаны
        top_k = top_k or self.top_k
        threshold = threshold or self.threshold

        logger.info(f"Retrieving passages for query: {query}")

        # Валидация запроса
        if not query or not query.strip():
            logger.warning("Empty query received")
            return []

        # Проверка на кэширование
        if hasattr(self.retrieve, 'cache_info'):
            cache_info = self.retrieve.cache_info()
            if cache_info.hits > self.cache_hits:
                self.cache_hits = cache_info.hits
                logger.info(f"Cache hit for query: {query}")

        try:
            # Токенизация запроса
            query_tokens = self._tokenize(query)

            if len(query_tokens) == 0:
                logger.warning(f"Query tokenized to empty list: {query}")
                return []

            # Расширение запроса синонимами
            if expand_query:
                expanded_tokens = self._expand_query(query_tokens)
                logger.info(f"Expanded query from {len(query_tokens)} to {len(expanded_tokens)} tokens")
            else:
                expanded_tokens = query_tokens

            # Быстрая предфильтрация по токенам
            candidate_indices = self._filter_by_tokens(expanded_tokens)

            if not candidate_indices:
                logger.info("No candidates found after token filtering")
                return []

            # Отладочная информация по кандидатам
            logger.info(f"Filtered candidates from {len(self.passages)} to {len(candidate_indices)}")

            # Получение scores
            if len(candidate_indices) < len(self.passages):
                # Используем отфильтрованный набор для скоринга
                filtered_passages = [self.tokenized_passages[i] for i in candidate_indices]

                # Создаем новый BM25 индекс для отфильтрованных пассажей
                if isinstance(self.bm25, BM25Plus):
                    temp_bm25 = BM25Plus(filtered_passages)
                else:
                    temp_bm25 = BM25Okapi(filtered_passages)

                # Получаем scores
                scores = temp_bm25.get_scores(expanded_tokens)

                # Сопоставляем индексы обратно
                indices_scores = [(candidate_indices[i], score) for i, score in enumerate(scores)]
            else:
                # Если фильтрация не помогла, используем полный индекс
                scores = self.bm25.get_scores(expanded_tokens)
                indices_scores = [(i, score) for i, score in enumerate(scores)]

            # Debug: print top scores
            top_scores = sorted(scores, reverse=True)[:5]
            logger.info(f"Top 5 scores: {top_scores}")

            # Сортировка по score
            indices_scores.sort(key=lambda x: x[1], reverse=True)

            # Формирование результатов
            results = []
            for idx, score in indices_scores[:top_k]:
                if score >= threshold:
                    results.append({
                        'text': self.passages[idx],
                        'score': float(score),  # Convert numpy float to Python float
                        'tokens': self.tokenized_passages[idx][:10]  # Первые 10 токенов для примера
                    })

            # Запись статистики
            self.last_query_time = time.time() - start_time

            logger.info(f"Found {len(results)} passages in {self.last_query_time:.3f} seconds")
            return results

        except Exception as e:
            logger.error(f"Error in retrieve: {str(e)}")
            self.last_query_time = time.time() - start_time
            return []

    def query_analysis(self, query: str) -> Dict[str, Any]:
        """
        Расширенный анализ запроса с метриками
        """
        start_time = time.time()

        try:
            # Токенизация запроса
            tokenized_query = self._tokenize(query)
            expanded_query = self._expand_query(tokenized_query)

            # Получение результатов
            results = self.retrieve(query)

            # Анализ токенов в результатах
            token_frequencies = {}
            for result in results:
                for token in result.get('tokens', []):
                    if token in token_frequencies:
                        token_frequencies[token] += 1
                    else:
                        token_frequencies[token] = 1

            # Сортировка токенов по частоте
            common_tokens = sorted(
                token_frequencies.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return {
                'query': query,
                'tokenized_query': tokenized_query,
                'expanded_query': expanded_query,
                'query_tokens_count': len(tokenized_query),
                'expanded_tokens_count': len(expanded_query),
                'results_count': len(results),
                'common_tokens': common_tokens,
                'execution_time': time.time() - start_time,
                'results': results
            }
        except Exception as e:
            logger.error(f"Error in query_analysis: {str(e)}")
            return {
                'query': query,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'results_count': 0,
                'results': []
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик производительности
        """
        cache_info = None
        if hasattr(self.retrieve, 'cache_info'):
            cache_info = self.retrieve.cache_info()

        return {
            'total_queries': self.query_count,
            'last_query_time': self.last_query_time,
            'cache_hits': self.cache_hits,
            'cache_info': cache_info,
            'passages_count': len(self.passages),
            'unique_tokens': len(self.inverted_index),
        }

    def dataset_info(self) -> Dict[str, Any]:
        """
        Расширенная информация о датасете
        """
        try:
            # Базовая информация
            info = {
                'total_passages': len(self.passages),
                'splits': {
                    split: len(self.dataset[split])
                    for split in ['train', 'validation', 'test']
                    if split in self.dataset
                }
            }

            # Статистика по длине passages
            passage_lengths = [len(p) for p in self.passages]
            info['passage_statistics'] = {
                'min_length': min(passage_lengths) if passage_lengths else 0,
                'max_length': max(passage_lengths) if passage_lengths else 0,
                'avg_length': sum(passage_lengths) / len(passage_lengths) if passage_lengths else 0,
                'median_length': sorted(passage_lengths)[len(passage_lengths) // 2] if passage_lengths else 0
            }

            # Статистика по токенам
            token_counts = [len(tokens) for tokens in self.tokenized_passages]
            info['token_statistics'] = {
                'min_tokens': min(token_counts) if token_counts else 0,
                'max_tokens': max(token_counts) if token_counts else 0,
                'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
                'total_tokens': sum(token_counts) if token_counts else 0
            }

            return info
        except Exception as e:
            logger.error(f"Error in dataset_info: {str(e)}")
            return {'error': str(e)}

    def search_with_filters(
            self,
            query: str,
            min_length: Optional[int] = None,
            max_length: Optional[int] = None,
            min_kazakh_chars: Optional[int] = None,
            top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск с дополнительными фильтрами
        """
        try:
            # Выполнение основного поиска
            results = self.retrieve(query, top_k=100)  # Получаем больше результатов для фильтрации

            # Применение фильтров
            filtered_results = []
            for result in results:
                text = result['text']

                # Фильтр по длине
                if min_length is not None and len(text) < min_length:
                    continue
                if max_length is not None and len(text) > max_length:
                    continue

                # Фильтр по количеству казахских символов
                if min_kazakh_chars is not None:
                    kazakh_chars = sum(1 for c in text if c in 'әіңғүұқөһ')
                    if kazakh_chars < min_kazakh_chars:
                        continue

                filtered_results.append(result)

            # Ограничение количества результатов
            top_k = top_k or self.top_k
            return filtered_results[:top_k]
        except Exception as e:
            logger.error(f"Error in search_with_filters: {str(e)}")
            return []

    def get_similar_passages(self, passage_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск passages, похожих на указанный
        """
        try:
            if passage_id < 0 or passage_id >= len(self.passages):
                raise ValueError(f"Invalid passage_id: {passage_id}, must be between 0 and {len(self.passages) - 1}")

            # Используем текст passage как запрос
            passage_text = self.passages[passage_id]

            # Получаем токены исходного passage
            source_tokens = self.tokenized_passages[passage_id]

            # Получаем scores для всех passages
            scores = self.bm25.get_scores(source_tokens)

            # Устанавливаем score исходного passage в 0, чтобы он не попал в результаты
            scores[passage_id] = 0

            # Сортировка и выбор top_k passages
            top_indices = np.argsort(scores)[-top_k:][::-1]

            results = [
                {
                    'text': self.passages[idx],
                    'score': float(scores[idx]),  # Convert numpy float to Python float
                    'passage_id': idx
                }
                for idx in top_indices
            ]

            return results
        except Exception as e:
            logger.error(f"Error in get_similar_passages: {str(e)}")
            return []

    def batch_retrieve(self, queries: List[str], top_k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Пакетный поиск для нескольких запросов
        """
        results = {}
        for query in queries:
            results[query] = self.retrieve(query, top_k=top_k)
        return results


def main():
    try:
        print("Initializing KazQAD Retrieval System...")

        # Инициализация retrieval системы с расширенными параметрами и пониженным порогом
        retrieval = KazQADRetrieval(bm25_variant='plus', use_stemming=True, threshold=0.1)

        # Информация о датасете
        print("\nИнформация о датасете:")
        dataset_info = retrieval.dataset_info()
        print(f"Общее количество passages: {dataset_info['total_passages']}")
        print(f"Распределение по split'ам: {dataset_info['splits']}")
        print(f"Статистика по длине: {dataset_info['passage_statistics']}")

        # Примеры запросов для тестирования
        queries = [
            "Қазақстан тарихы",
            "Абай Құнанбаев",
            "Қазақстан астанасы",
            "Алматы қаласы",
            "Қазақ әдебиеті"
        ]

        # Тестирование различных запросов
        for query in queries:
            print(f"\nПоиск по запросу: {query}")

            # Стандартный поиск
            results = retrieval.retrieve(query)

            print(f"Найдено {len(results)} результатов:")
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {result['score']:.2f}")
                print(f"   Text: {result['text'][:150]}...\n")

            # Анализ запроса
            analysis = retrieval.query_analysis(query)
            print(f"Анализ запроса:")
            print(f"- Токены запроса: {analysis['tokenized_query']}")
            print(f"- Расширенные токены: {analysis['expanded_query']}")
            print(f"- Время выполнения: {analysis['execution_time']:.3f} сек")

        # Метрики производительности
        print("\nМетрики производительности:")
        metrics = retrieval.get_performance_metrics()
        print(f"Всего запросов: {metrics['total_queries']}")
        print(f"Время последнего запроса: {metrics['last_query_time']:.3f} сек")
        print(f"Кэш-попаданий: {metrics['cache_hits']}")

    except Exception as e:
        print(f"Ошибка выполнения: {str(e)}")
        logger.error(f"Main execution error: {str(e)}")


if __name__ == "__main__":
    main()