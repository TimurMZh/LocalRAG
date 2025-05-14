# Векторное хранилище

## Понимание векторов в AI системах

Векторные эмбеддинги - это числовые представления данных (текста, изображений и т.д.), которые захватывают семантическое значение в многомерном пространстве. Эти эмбеддинги обеспечивают:

- Возможности семантического поиска
- Сравнение по схожести
- Эффективный поиск информации
- Контекстно-зависимые AI операции

## Почему PostgreSQL?

Использование PostgreSQL с pgvectorscale в качестве векторной базы данных предлагает несколько ключевых преимуществ по сравнению со специализированными векторными базами данных:

- PostgreSQL - это надежная база данных с открытым исходным кодом, имеющая богатую экосистему инструментов, драйверов и коннекторов. Это обеспечивает прозрачность, поддержку сообщества и постоянные улучшения.

- Используя PostgreSQL, вы можете управлять как реляционными, так и векторными данными в одной базе данных. Это снижает операционную сложность, так как нет необходимости поддерживать и синхронизировать несколько баз данных.

- Pgvectorscale расширяет возможности pgvector, обеспечивая более быстрый поиск, более высокую точность и эффективную фильтрацию по времени. Он использует продвинутые техники индексирования, такие как индекс на основе DiskANN, для значительного ускорения поиска ближайших соседей (ANN).

Pgvectorscale Vector построен поверх [pgvector](https://github.com/pgvector/pgvector), предлагая улучшенную производительность и дополнительные возможности, что делает PostgreSQL мощным и универсальным выбором для AI приложений.

## Текущая реализация

Наша векторная реализация PostgreSQL использует векторное расширение TimescaleDB:

```python
class VectorStore:
    def __init__(self, session: Session):
        self.session = session
        self.config = get_settings().database.vector_store

    async def create_embedding(self, text: str, metadata: Dict = None) -> UUID:
        # Create embedding using configured provider
        embedding = await self.create_embedding_vector(text)
        
        # Store in PostgreSQL with TimescaleDB vector
        vector_id = await self.store_vector(
            embedding=embedding,
            metadata=metadata
        )
        return vector_id
```

### Schema Setup

```sql
-- Enable vector extension
CREATE EXTENSION vector;

-- Create hypertable with vector support
CREATE TABLE embeddings (
    id uuid PRIMARY KEY,
    embedding vector(1536),
    metadata jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

-- Create vector index
CREATE INDEX ON embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Расширение или замена векторного хранилища

Реализация векторного хранилища разработана для заменяемости. Вы можете реализовать свое собственное векторное хранилище, следуя этим шагам:

1. Создайте новый класс векторного хранилища:
```python
class CustomVectorStore:
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        # Initialize your vector store

    def create_embedding(
        self,
        text: str,
        metadata: Dict = None
    ) -> str:
        # Implement embedding creation and storage
        pass

    def search(
        self,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict]:
        # Implement similarity search
        pass
```

2. Обновите конфигурацию:
```python
# config/database_config.py
class VectorStoreConfig(BaseSettings):
    provider: str = "custom"  # or "postgres", "pinecone", etc.
    # Additional provider-specific settings
```

### Популярные альтернативы

Вы можете рассмотреть эти альтернативы в зависимости от ваших потребностей:
1. **Pinecone**
   - Специализированная векторная база данных
   - Управляемый сервис
   - Высокая производительность
   - Встроенное масштабирование

2. **Weaviate**
   - Мультимодальные векторы
   - Богатые возможности запросов
   - GraphQL интерфейс
   - Возможность самостоятельного хостинга

3. **Qdrant**
   - Производительность на базе Rust
   - Богатая фильтрация
   - Простое развертывание
   - Активная разработка

## Соображения производительности

При использовании PostgreSQL для векторов:

1. **Индексирование**
   - Используйте подходящие типы индексов (IVFFlat, HNSW)
   - Настраивайте параметры индекса в зависимости от размера данных
   - Регулярное обслуживание индексов

2. **Партиционирование**
   - TimescaleDB гипертаблицы для партиционирования по времени
   - Партиционирование по атрибутам метаданных при необходимости
   - Балансировка размеров партиций

