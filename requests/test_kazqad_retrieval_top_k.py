import io
import sys
import requests
import argparse
import logging
import time
import json
import numpy as np
from datasets import load_dataset
from tqdm import tqdm
import uuid
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Обеспечиваем корректный вывод символов в консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kazqad_test.log"),
        logging.StreamHandler(stream=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    ]
)
logger = logging.getLogger(__name__)


# Функция загрузки датасета
def load_kazqad_dataset(split="test", limit=None):
    """Load the KazQAD dataset from Hugging Face"""
    try:
        dataset = load_dataset("issai/kazqad-retrieval")[split]
        logger.info(f"Successfully loaded KazQAD {split} dataset with {len(dataset)} items")

        if limit:
            dataset = dataset.select(range(min(limit, len(dataset))))
            logger.info(f"Limited dataset to {len(dataset)} items")

        return dataset
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        raise


# Функция для расчета Top-k accuracy
def calculate_topk_accuracy(similarities, positive_indices_list, k=3):
    """
    Рассчитывает Top-k accuracy - долю запросов, для которых хотя бы один
    положительный пассаж находится среди топ-k результатов

    Args:
        similarities: список списков схожестей запросов с документами
        positive_indices_list: список списков индексов положительных пассажей
                              для каждого запроса
        k: количество топ результатов для проверки

    Returns:
        float: Top-k accuracy (от 0 до 1)
    """
    correct = 0
    total = len(similarities)

    for i, sim_list in enumerate(similarities):
        # Получаем индексы топ-k пассажей с наивысшим сходством
        top_indices = np.argsort(sim_list)[-k:]

        # Проверяем, есть ли хотя бы один положительный пассаж в топ-k
        if any(pos_idx in top_indices for pos_idx in positive_indices_list[i]):
            correct += 1

    return correct / total if total > 0 else 0.0


# Функция для расчета MRR (Mean Reciprocal Rank)
def calculate_mrr(similarities, positive_indices_list):
    """
    Рассчитывает MRR (Mean Reciprocal Rank) - среднее значение обратного ранга
    первого релевантного документа в списке результатов

    Args:
        similarities: список списков схожестей запросов с документами
        positive_indices_list: список списков индексов положительных пассажей

    Returns:
        float: MRR значение (от 0 до 1)
    """
    reciprocal_ranks = []

    for i, sim_list in enumerate(similarities):
        # Сортируем индексы по убыванию схожести
        sorted_indices = np.argsort(sim_list)[::-1]

        # Находим ранг первого положительного пассажа
        for rank, idx in enumerate(sorted_indices, 1):
            if idx in positive_indices_list[i]:
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            # Если положительный пассаж не найден
            reciprocal_ranks.append(0.0)

    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0


# Основная функция тестирования
def test_retrieval_system(dataset, api_url, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                          batch_size=1, delay=0.1):
    """Test the retrieval system with the KazQAD dataset"""
    # Загружаем модель для создания эмбеддингов
    try:
        model = SentenceTransformer(model_name)
        logger.info(f"Successfully loaded model: {model_name}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    # Инициализация счётчиков
    results = {
        "total": len(dataset),
        "successful": 0,
        "failed": 0,
        "failed_items": [],
        "topk_accuracy": {},
        "mrr": 0.0
    }

    all_queries = []
    all_similarities = []
    all_positive_indices = []

    for i, item in enumerate(tqdm(dataset, desc="Testing queries")):
        # Извлекаем запрос
        query = item["query"]
        all_queries.append(query)

        # Проверяем структуру positive_passages и negative_passages
        if len(item["positive_passages"]) > 0:
            if isinstance(item["positive_passages"][0], dict) and "text" in item["positive_passages"][0]:
                positive = [p["text"] for p in item["positive_passages"]]
            else:
                positive = item["positive_passages"]
        else:
            positive = []

        if len(item["negative_passages"]) > 0:
            if isinstance(item["negative_passages"][0], dict) and "text" in item["negative_passages"][0]:
                negative = [n["text"] for n in item["negative_passages"]]
            else:
                negative = item["negative_passages"]
        else:
            negative = []

        # Собираем все passages для запроса
        all_passages = positive + negative

        # Запоминаем индексы положительных passages для этого запроса
        positive_indices = list(range(len(positive)))
        all_positive_indices.append(positive_indices)

        # Создаем эмбеддинги для запроса и passages
        query_embedding = model.encode(query)
        passage_embeddings = model.encode(all_passages)

        # Рассчитываем косинусную схожесть
        similarities = cosine_similarity([query_embedding], passage_embeddings)[0]
        all_similarities.append(similarities)

        # Формируем запрос для API
        data = {
            "query_id": item["query_id"],
            "query": query,
            "positive": positive,
            "negative": negative,
            "ticket_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "from_email": "user@example.com",
            "to_email": "dockerDatabase@example.com",
            "sender": "KazQAD Test",
            "subject": f"Query: {item['query_id']}",
            "body": query
        }

        # Добавим отладочную информацию для первого запроса
        if i == 0:
            try:
                logger.info(f"Sample request data: {json.dumps(data, ensure_ascii=False)[:500]}...")

                # Выводим примеры схожестей для отладки
                sorted_sim_indices = np.argsort(similarities)[::-1]
                logger.info("Top-3 similarities for first query:")
                for idx in sorted_sim_indices[:3]:
                    is_positive = idx in positive_indices
                    logger.info(
                        f"  Rank {list(sorted_sim_indices).index(idx) + 1}: {similarities[idx]:.4f} {'(positive)' if is_positive else '(negative)'}")
            except UnicodeEncodeError:
                print("⚠ Не удалось вывести Kazakh текст в консоль (logger), но всё работает.")

        try:
            # Отправляем запрос к API
            response = requests.post(api_url, json=data, timeout=30)
            if response.status_code in [200, 202]:
                results["successful"] += 1
                logger.debug(f"Item {i + 1}/{len(dataset)}: Success")
            else:
                results["failed"] += 1
                error_info = {
                    "query_id": item["query_id"],
                    "status_code": response.status_code,
                    "response": response.text[:100] + "..." if len(response.text) > 100 else response.text
                }
                results["failed_items"].append(error_info)
                logger.warning(f"Item {i + 1}/{len(dataset)}: Failed with status {response.status_code}")
        except Exception as e:
            results["failed"] += 1
            error_info = {
                "query_id": item["query_id"],
                "exception": str(e)
            }
            results["failed_items"].append(error_info)
            logger.error(f"Item {i + 1}/{len(dataset)}: Exception - {e}")

        # Добавляем задержку между запросами
        if delay > 0 and i < len(dataset) - 1:
            time.sleep(delay)

        # Логируем прогресс каждые batch_size элементов
        if (i + 1) % batch_size == 0:
            logger.info(f"Progress: {i + 1}/{len(dataset)} items processed")

    # Рассчитываем Top-k accuracy для разных значений k
    for k in [1, 3, 5, 10]:
        topk = calculate_topk_accuracy(all_similarities, all_positive_indices, k=k)
        results["topk_accuracy"][k] = topk
        logger.info(f"Top-{k} accuracy: {topk:.4f}")

    # Рассчитываем MRR
    mrr = calculate_mrr(all_similarities, all_positive_indices)
    results["mrr"] = mrr
    logger.info(f"MRR: {mrr:.4f}")

    return results


def print_summary(results):
    """Print a summary of the test results"""
    success_rate = (results["successful"] / results["total"]) * 100 if results["total"] > 0 else 0

    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total queries: {results['total']}")
    logger.info(f"Successful: {results['successful']} ({success_rate:.2f}%)")
    logger.info(f"Failed: {results['failed']} ({100 - success_rate:.2f}%)")

    # Выводим метрики качества поиска
    logger.info("\nRETRIEVAL METRICS:")
    for k, accuracy in results.get("topk_accuracy", {}).items():
        logger.info(f"Top-{k} accuracy: {accuracy:.4f}")

    logger.info(f"Mean Reciprocal Rank (MRR): {results.get('mrr', 0):.4f}")

    if results["failed_items"]:
        logger.info("\nFailed Items:")
        for item in results["failed_items"][:10]:
            logger.info(f"- Query ID: {item['query_id']}")
            if "status_code" in item:
                logger.info(f"  Status: {item['status_code']}")
                logger.info(f"  Response: {item['response']}")
            else:
                logger.info(f"  Exception: {item['exception']}")

        if len(results["failed_items"]) > 10:
            logger.info(f"... and {len(results['failed_items']) - 10} more failures (see log file)")


def main():
    parser = argparse.ArgumentParser(description="Test retrieval system with KazQAD dataset")
    parser.add_argument("--api-url", default="http://localhost:8080/events",
                        help="URL of the API endpoint (default: http://localhost:8080/events)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit the number of test items (default: use all)")
    parser.add_argument("--split", default="test",
                        help="Dataset split to use (default: test)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Log progress every N items (default: 10)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="Delay between requests in seconds (default: 0.1)")
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        help="Model name for creating embeddings (default: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)")

    args = parser.parse_args()

    logger.info(f"Starting KazQAD retrieval test with the following parameters:")
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"Dataset split: {args.split}")
    logger.info(f"Item limit: {args.limit if args.limit else 'None (using all items)'}")
    logger.info(f"Request delay: {args.delay} seconds")
    logger.info(f"Model: {args.model}")

    # Load the dataset
    dataset = load_kazqad_dataset(split=args.split, limit=args.limit)

    # Run the test
    start_time = time.time()
    results = test_retrieval_system(
        dataset,
        args.api_url,
        model_name=args.model,
        batch_size=args.batch_size,
        delay=args.delay
    )
    end_time = time.time()

    # Print summary
    print_summary(results)
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()