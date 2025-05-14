import io  # Импорт модуля io для операций ввода-вывода
import sys  # Импорт модуля sys для доступа к системным функциям
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')  # Настройка стандартного вывода для поддержки UTF-8
#Обеспечивает корректный вывод казахских символов в консоли Windows.  # Комментарий о назначении настройки кодировки
import requests  # Импорт модуля requests для HTTP-запросов
import argparse  # Импорт модуля argparse для обработки аргументов командной строки
import logging  # Импорт модуля logging для ведения журнала событий
import time  # Импорт модуля time для управления временем и задержками
import json  # Импорт модуля json для работы с JSON-данными
from datasets import load_dataset  # Импорт функции load_dataset из модуля datasets для загрузки датасетов
from tqdm import tqdm  # Импорт класса tqdm для отображения прогресс-бара
import uuid  # Импорт модуля uuid для генерации уникальных идентификаторов
from datetime import datetime  # Импорт класса datetime для работы с датой и временем


# Настройка логгера  # Комментарий, указывающий на начало настройки логирования
logging.basicConfig(  # Базовая настройка системы логирования
    level=logging.INFO,  # Установка уровня логирования на INFO (будут выводиться INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Установка формата вывода логов (время, уровень, сообщение)
    handlers=[  # Список обработчиков, определяющих куда будут выводиться логи
        logging.FileHandler("kazqad_test.log"),  # Обработчик для записи логов в файл kazqad_test.log
        logging.StreamHandler(stream=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))  # Обработчик для вывода в консоль с UTF-8
    ]
)
logger = logging.getLogger(__name__)  # Создание объекта логгера для текущего модуля

#Функция загрузки датасета  # Комментарий, указывающий на начало определения функции загрузки датасета
def load_kazqad_dataset(split="test", limit=None):  # Определение функции с параметрами split (раздел) и limit (ограничение)
    """Load the KazQAD dataset from Hugging Face"""  # Документационная строка с описанием функции
    try:  # Начало блока обработки исключений
        dataset = load_dataset("issai/kazqad-retrieval")[split]  # Загрузка датасета issai/kazqad-retrieval и выбор указанного раздела
        logger.info(f"Successfully loaded KazQAD {split} dataset with {len(dataset)} items")  # Логирование успешной загрузки с указанием количества элементов

        if limit:  # Проверка, указано ли ограничение
            dataset = dataset.select(range(min(limit, len(dataset))))  # Выбор только первых N элементов (не больше чем есть)
            logger.info(f"Limited dataset to {len(dataset)} items")  # Логирование факта ограничения с указанием итогового количества

        return dataset  # Возвращение загруженного (и возможно ограниченного) датасета
    except Exception as e:  # Обработка любых исключений при загрузке
        logger.error(f"Failed to load dataset: {e}")  # Логирование ошибки загрузки
        raise  # Повторное возбуждение исключения для обработки на более высоком уровне

# Основная функция тестирования  # Комментарий, указывающий на начало определения основной функции тестирования
def test_retrieval_system(dataset, api_url, batch_size=1, delay=0.1):  # Определение функции с параметрами
    """Test the retrieval system with the KazQAD dataset"""  # Документационная строка с описанием функции
    #Инициализация счётчиков  # Комментарий о назначении следующего блока
    results = {  # Создание словаря для хранения результатов тестирования
        "total": len(dataset),  # Общее количество элементов для тестирования
        "successful": 0,  # Начальное значение счётчика успешных запросов
        "failed": 0,  # Начальное значение счётчика неудачных запросов
        "failed_items": []  # Пустой список для хранения информации о неудачных запросах
    }

    for i, item in enumerate(tqdm(dataset, desc="Testing queries")):  # Цикл по элементам датасета с отображением прогресса
        # Проверяем структуру positive_passages и negative_passages  # Комментарий о назначении следующего блока
        if len(item["positive_passages"]) > 0:  # Проверка, есть ли положительные примеры
            # Если это список словарей, извлекаем только текст  # Комментарий о проверке типа данных
            if isinstance(item["positive_passages"][0], dict) and "text" in item["positive_passages"][0]:  # Проверка, является ли первый элемент словарём с ключом "text"
                positive = [p["text"] for p in item["positive_passages"]]  # Извлечение только текста из каждого словаря
            else:  # Если это не словари с ключом "text"
                positive = item["positive_passages"]  # Использование исходного списка
        else:  # Если положительных примеров нет
            positive = []  # Инициализация пустым списком

        if len(item["negative_passages"]) > 0:  # Проверка, есть ли отрицательные примеры
            # Если это список словарей, извлекаем только текст  # Комментарий о проверке типа данных
            if isinstance(item["negative_passages"][0], dict) and "text" in item["negative_passages"][0]:  # Проверка, является ли первый элемент словарём с ключом "text"
                negative = [n["text"] for n in item["negative_passages"]]  # Извлечение только текста из каждого словаря
            else:  # Если это не словари с ключом "text"
                negative = item["negative_passages"]  # Использование исходного списка
        else:  # Если отрицательных примеров нет
            negative = []  # Инициализация пустым списком

        # Формируем запрос в соответствии с ожидаемой структурой / Формирование JSON-запроса / Этот JSON будет отправлен в /events  # Комментарий о назначении следующего блока
        data = {  # Создание словаря с данными для JSON-запроса
            "query_id": item["query_id"],  # ID запроса из датасета
            "query": item["query"],  # Текст запроса из датасета
            "positive": positive,  # Обработанные положительные примеры
            "negative": negative,  # Обработанные отрицательные примеры
            "ticket_id": str(uuid.uuid4()),  # Генерация уникального ID тикета
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),  # Текущее время в формате ISO 8601
            "from_email": "user@example.com",  # Email отправителя
            # Вот здесь меняем на допустимый email  # Комментарий о важном изменении
            "to_email": "support@example.com",  # Email получателя (support для использования CustomerSupportPipeline)
            "sender": "KazQAD Test",  # Имя отправителя
            "subject": f"Query: {item['query_id']}",  # Тема сообщения, включающая ID запроса
            "body": item["query"]  # Тело сообщения, содержащее текст запроса
        }

        # Добавим отладочную информацию  # Комментарий о назначении следующего блока
        if i == 0:  # Проверка, является ли это первым элементом
            logger.info(f"Sample request data: {json.dumps(data, ensure_ascii=False)[:500]}...")  # Логирование примера данных запроса (не более 500 символов)

        try:  # Начало блока обработки исключений
            # Отправляем запрос к API  # Комментарий о назначении следующей строки
            response = requests.post(api_url, json=data, timeout=30)  # Отправка POST-запроса с таймаутом 30 секунд
            #В случае ошибки — логируется и сохраняется query_id, код и тело ответа  # Комментарий о назначении следующего блока
            if response.status_code in [200, 202]:  # Проверка, является ли статус-код успешным (200 или 202)
                results["successful"] += 1  # Увеличение счётчика успешных запросов
                logger.debug(f"Item {i + 1}/{len(dataset)}: Success")  # Логирование успешного запроса на уровне DEBUG
            else:  # Если статус-код не 200 и не 202
                results["failed"] += 1  # Увеличение счётчика неудачных запросов
                error_info = {  # Создание словаря с информацией об ошибке
                    "query_id": item["query_id"],  # ID запроса
                    "status_code": response.status_code,  # Статус-код ответа
                    "response": response.text[:100] + "..." if len(response.text) > 100 else response.text  # Тело ответа (до 100 символов)
                }
                results["failed_items"].append(error_info)  # Добавление информации об ошибке в список
                logger.warning(f"Item {i + 1}/{len(dataset)}: Failed with status {response.status_code}")  # Логирование неудачного запроса
        #Если requests.post упал с ошибкой соединения и т.п  # Комментарий о назначении следующего блока
        except Exception as e:  # Обработка исключений при отправке запроса
            results["failed"] += 1  # Увеличение счётчика неудачных запросов
            error_info = {  # Создание словаря с информацией об ошибке
                "query_id": item["query_id"],  # ID запроса
                "exception": str(e)  # Текст исключения
            }
            results["failed_items"].append(error_info)  # Добавление информации об ошибке в список
            logger.error(f"Item {i + 1}/{len(dataset)}: Exception - {e}")  # Логирование исключения

        # Добавляем задержку между запросами  # Комментарий о назначении следующего блока
        if delay > 0 and i < len(dataset) - 1:  # Проверка, нужна ли задержка и не последний ли это элемент
            time.sleep(delay)  # Пауза на указанное количество секунд

        # Логируем прогресс каждые batch_size элементов  # Комментарий о назначении следующего блока
        if (i + 1) % batch_size == 0:  # Проверка, кратно ли количество обработанных элементов размеру пакета
            logger.info(f"Progress: {i + 1}/{len(dataset)} items processed")  # Логирование прогресса

    return results  # Возвращение результатов тестирования

def print_summary(results):  # Определение функции для вывода итогов
    """Print a summary of the test results"""  # Документационная строка с описанием функции
    success_rate = (results["successful"] / results["total"]) * 100 if results["total"] > 0 else 0  # Вычисление процента успешных запросов

    logger.info("=" * 50)  # Вывод разделителя
    logger.info("TEST SUMMARY")  # Вывод заголовка
    logger.info("=" * 50)  # Вывод разделителя
    logger.info(f"Total queries: {results['total']}")  # Вывод общего количества запросов
    logger.info(f"Successful: {results['successful']} ({success_rate:.2f}%)")  # Вывод количества и процента успешных запросов
    logger.info(f"Failed: {results['failed']} ({100 - success_rate:.2f}%)")  # Вывод количества и процента неудачных запросов

    if results["failed_items"]:  # Проверка, есть ли неудачные запросы
        logger.info("\nFailed Items:")  # Вывод заголовка для неудачных запросов
        for item in results["failed_items"][:10]:  # Цикл по первым 10 неудачным запросам
            logger.info(f"- Query ID: {item['query_id']}")  # Вывод ID запроса
            if "status_code" in item:  # Проверка, есть ли статус-код
                logger.info(f"  Status: {item['status_code']}")  # Вывод статус-кода
                logger.info(f"  Response: {item['response']}")  # Вывод тела ответа
            else:  # Если статус-кода нет
                logger.info(f"  Exception: {item['exception']}")  # Вывод текста исключения

        if len(results["failed_items"]) > 10:  # Проверка, больше ли 10 неудачных запросов
            logger.info(f"... and {len(results['failed_items']) - 10} more failures (see log file)")  # Вывод информации о количестве оставшихся неудачных запросов


def main():  # Определение основной функции
    parser = argparse.ArgumentParser(description="Test retrieval system with KazQAD dataset")  # Создание парсера аргументов
    parser.add_argument("--api-url", default="http://localhost:8080/events",  # Добавление аргумента --api-url
                        help="URL of the API endpoint (default: http://localhost:8080/events)")  # Справка для аргумента
    parser.add_argument("--limit", type=int, default=None,  # Добавление аргумента --limit
                        help="Limit the number of test items (default: use all)")  # Справка для аргумента
    parser.add_argument("--split", default="test",  # Добавление аргумента --split
                        help="Dataset split to use (default: test)")  # Справка для аргумента
    parser.add_argument("--batch-size", type=int, default=10,  # Добавление аргумента --batch-size
                        help="Log progress every N items (default: 10)")  # Справка для аргумента
    parser.add_argument("--delay", type=float, default=0.1,  # Добавление аргумента --delay
                        help="Delay between requests in seconds (default: 0.1)")  # Справка для аргумента

    args = parser.parse_args()  # Разбор аргументов командной строки

    logger.info(f"Starting KazQAD retrieval test with the following parameters:")  # Логирование начала теста
    logger.info(f"API URL: {args.api_url}")  # Логирование URL API
    logger.info(f"Dataset split: {args.split}")  # Логирование раздела датасета
    logger.info(f"Item limit: {args.limit if args.limit else 'None (using all items)'}")  # Логирование ограничения элементов
    logger.info(f"Request delay: {args.delay} seconds")  # Логирование задержки между запросами

    # Load the dataset  # Комментарий о назначении следующей строки
    dataset = load_kazqad_dataset(split=args.split, limit=args.limit)  # Загрузка датасета с указанными параметрами

    # Run the test  # Комментарий о назначении следующего блока
    start_time = time.time()  # Запись времени начала теста
    results = test_retrieval_system(  # Запуск функции тестирования
        dataset,  # Передача датасета
        args.api_url,  # Передача URL API
        batch_size=args.batch_size,  # Передача размера пакета
        delay=args.delay  # Передача задержки между запросами
    )
    end_time = time.time()  # Запись времени окончания теста

    # Print summary  # Комментарий о назначении следующего блока
    print_summary(results)  # Вывод итогов тестирования
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds")  # Логирование общего времени выполнения


if __name__ == "__main__":  # Проверка, запущен ли скрипт как самостоятельная программа
    main()  # Запуск основной функции