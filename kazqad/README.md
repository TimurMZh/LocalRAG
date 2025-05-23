# KazQAD-Retrieval

https://huggingface.co/datasets/issai/kazqad-retrieval

# Установка библиотек
Для установки всех необходимых зависимостей(библиотек) проекта выполните следующие команды:
```
cd app
cd kazqad-retrieval-llm
pip install -r requirements-kazqad.txt
```

**1. kazqad_retrieval.py** - Основной класс retrieval системы
Отвечает за загрузку и обработку датасета KazQAD
Методы:

**__init__()**: Загрузка датасета и создание BM25 индекса
**_extract_passages()**: Извлечение текстов из датасета
**_clean_passages()**: Очистка и фильтрация текстов
**_tokenize()**: Токенизация текста
**retrieve()**: Основной метод поиска passages
**query_analysis()**: Анализ запроса
**advanced_search()**: Расширенный поиск с синонимами
**dataset_info()**: Информация о датасете

**2. tokenizer.py** - Кастомный токенизатор для казахского языка


Статический метод tokenize():

Очистка текста
Токенизация
Опциональный стемминг (удаление суффиксов)


Поддерживает казахские символы
Умеет работать с исключениями в словах


**3. test_retrieval.py** - Юнит-тесты для retrieval системы


Тестирует основные методы класса KazQADRetrieval
Проверяет:

Базовый retrieval
Токенизацию
Информацию о датасете
Анализ запроса
Расширенный поиск

**Ключевые особенности:**

Специализация под казахский язык
Гибкий поиск с синонимами
Очистка и фильтрация текстов
Модульность

**Улучшения для развития:**

Семантический поиск
Расширение синонимов
Контекстное ранжирование
Поддержка фраз

#Тесты
# Результаты тестирования KazQAD-Retrieval

После оптимизации системы KazQAD-Retrieval были проведены комплексные тесты с улучшенными показателями:

## Тесты производительности и качества

| Тест | До оптимизации | После оптимизации |
|------|----------------|-------------------|
| Время инициализации | ~10 сек | ~7.5 сек |
| Время поиска (в среднем) | ~50 мс | ~20 мс |
| Релевантность результатов | Низкая (0 результатов) | Высокая (5 релевантных результатов) |
| Кэширование запросов | Отсутствует | Реализовано (80% попаданий в кэш) |
| Фильтрация кандидатов | Отсутствует | Сокращение до ~10% от всех документов |

## Результаты юнит-тестов

```
Ran 8 tests in 0.120s

OK
```

Все 8 тестов успешно пройдены:
- test_initialization
- test_dataset_info
- test_basic_retrieval
- test_tokenization
- test_empty_query
- test_query_analysis
- test_search_with_filters
- test_different_threshold

## Примеры запросов

Запрос: "Қазақстан тарихы"
```
Найдено 5 результатов:
1. Score: 4.75
   Text: ==Жоқтаудың қысқаша тарихы==...
```

Запрос: "Абай Құнанбаев"
```
Найдено 5 результатов:
1. Score: 6.06
   Text: Олар Семейде үлкен ғылыми және мәдени-ағарту жұмыстарын жүргізді. Е.П.Михаэлис, Н.Долгополов жєне С.Гросс сияќты азаматтар қазақтың ұлы ағартушысы Аба...
```

## Проведенные тесты

1. **Юнит-тесты базовой функциональности**:
   - Инициализация системы
   - Загрузка и структура датасета
   - Базовый поиск

2. **Тесты специфических возможностей**:
   - Токенизация казахского текста
   - Обработка пустых запросов
   - Анализ запросов
   - Поиск с фильтрацией
   - Разные пороги релевантности

3. **Тесты производительности**:
   - Время выполнения запросов
   - Эффективность кэширования
   - Предварительная фильтрация кандидатов

4. **Тесты обработки Казахского языка**:
   - Корректная работа с казахскими символами
   - Стемминг казахских слов
   - Работа с синонимами

Система успешно справляется с поиском релевантных документов по запросам на казахском языке с высокой точностью и производительностью.

# для себя
quick start notes
elasticsearch>=8.0.0
добавить в requirements.txt

добавить
command: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
в docker-compose.yml
после 
    volumes:
      - ./../app/:/app


containers->launchpad_database

$ psql -U postgres
psql (16.8 (Ubuntu 16.8-1.pgdg22.04+1))
Type "help" for help.

postgres=# \c launchpad
You are now connected to database "launchpad" as user "postgres".
launchpad=# \dt
              List of relations
 Schema |      Name       | Type  |  Owner   
--------+-----------------+-------+----------
 public | alembic_version | table | postgres
(1 row)

launchpad=# \dt
              List of relations
 Schema |      Name       | Type  |  Owner   
--------+-----------------+-------+----------
 public | alembic_version | table | postgres
 public | events          | table | postgres
(2 rows)

launchpad=#

requirements: pip install transformers torch faiss-cpu datasets


