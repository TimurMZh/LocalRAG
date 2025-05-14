import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
#Обеспечивает корректный вывод казахских символов в консоли Windows.
import requests # отправка POST-запросов.
import argparse # разбор аргументов командной строки
import logging # логирование
import time
import json
from datasets import load_dataset # загрузка KazQAD с HuggingFace
from tqdm import tqdm # визуальный прогрессбар
import uuid # генерация ID и времени
from datetime import datetime


# Настройка логгера
logging.basicConfig(
    level=logging.INFO,#уровень логирования (будут выводиться INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s', #формат сообщений лога (время - уровень - сообщение)
    handlers=[  #Два обработчика
        logging.FileHandler("kazqad_test.log"), #В файл kazqad_test.log
        logging.StreamHandler(stream=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')) #В консоль (в UTF-8, чтобы не крашилась)
    ]
)
logger = logging.getLogger(__name__) #создание объекта логгера для текущего модуля

#Функция загрузки датасета
def load_kazqad_dataset(split="test", limit=None): #split раздел датасета (по умолчанию "test")
    #limit - ограничение количества элементов (по умолчанию None - загрузка всех)
    """Load the KazQAD dataset from Hugging Face"""
    try:
        dataset = load_dataset("issai/kazqad-retrieval")[split] #Загружает test-раздел KazQAD
        logger.info(f"Successfully loaded KazQAD {split} dataset with {len(dataset)} items")

        if limit:
            dataset = dataset.select(range(min(limit, len(dataset)))) #Если указан limit, выбирает только первые N элементов
            logger.info(f"Limited dataset to {len(dataset)} items")

        return dataset
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        raise

# Основная функция тестирования
def test_retrieval_system(dataset, api_url, batch_size=1, delay=0.1):
    """Test the retrieval system with the KazQAD dataset"""
    #Инициализация счётчиков
    results = {
        "total": len(dataset),
        "successful": 0,
        "failed": 0,
        "failed_items": []
    }

    for i, item in enumerate(tqdm(dataset, desc="Testing queries")): #Обработка каждого элемента датасета
        # Проверяем структуру positive_passages и negative_passages
        if len(item["positive_passages"]) > 0:
            # Если это список словарей, извлекаем только текст
            if isinstance(item["positive_passages"][0], dict) and "text" in item["positive_passages"][0]:
                positive = [p["text"] for p in item["positive_passages"]]
            else:
                positive = item["positive_passages"]
        else:
            positive = []

        if len(item["negative_passages"]) > 0:
            # Если это список словарей, извлекаем только текст
            if isinstance(item["negative_passages"][0], dict) and "text" in item["negative_passages"][0]:
                negative = [n["text"] for n in item["negative_passages"]]
            else:
                negative = item["negative_passages"]
        else:
            negative = []

        # Формируем запрос в соответствии с ожидаемой структурой / Формирование JSON-запроса / Этот JSON будет отправлен в /events
        data = {
            "query_id": item["query_id"],
            "query": item["query"],
            "positive": positive,
            "negative": negative,
            "ticket_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "from_email": "user@example.com",
            # Вот здесь меняем на допустимый email
            "to_email": "support@example.com",
            "sender": "KazQAD Test",
            "subject": f"Query: {item['query_id']}",
            "body": item["query"]
        }

        # Добавим отладочную информацию
        if i == 0:  # Только для первого запроса
            logger.info(f"Sample request data: {json.dumps(data, ensure_ascii=False)[:500]}...")

        try:
            # Отправляем запрос к API
            response = requests.post(api_url, json=data, timeout=30) # API должен вернуть 202 или 200
            #В случае ошибки — логируется и сохраняется query_id, код и тело ответа
            if response.status_code in [200, 202]: #Отправка POST-запроса / Проверка результата
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
        #Если requests.post упал с ошибкой соединения и т.п
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

    return results

def print_summary(results): # Вывод итогов
    """Print a summary of the test results"""
    success_rate = (results["successful"] / results["total"]) * 100 if results["total"] > 0 else 0

    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total queries: {results['total']}")
    logger.info(f"Successful: {results['successful']} ({success_rate:.2f}%)")
    logger.info(f"Failed: {results['failed']} ({100 - success_rate:.2f}%)")

    if results["failed_items"]:
        logger.info("\nFailed Items:")
        for item in results["failed_items"][:10]:  # Show first 10 failures
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

    args = parser.parse_args()

    logger.info(f"Starting KazQAD retrieval test with the following parameters:")
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"Dataset split: {args.split}")
    logger.info(f"Item limit: {args.limit if args.limit else 'None (using all items)'}")
    logger.info(f"Request delay: {args.delay} seconds")

    # Load the dataset
    dataset = load_kazqad_dataset(split=args.split, limit=args.limit)

    # Run the test
    start_time = time.time()
    results = test_retrieval_system(
        dataset,
        args.api_url,
        batch_size=args.batch_size,
        delay=args.delay
    )
    end_time = time.time()

    # Print summary
    print_summary(results)
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()