# Интеграция с Elasticsearch

## Обзор

Elasticsearch служит нашим основным поисковым движком, дополняя PostgreSQL и векторное хранилище. Он обеспечивает:
- Возможности полнотекстового поиска
- Быстрое извлечение документов
- Гибкие запросы с оценкой релевантности
- Масштабируемое индексирование документов

## Реализация

### Базовая конфигурация

```python
from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Optional

class ElasticsearchClient:
    def __init__(self):
        self.client = AsyncElasticsearch(
            hosts=[f"{os.getenv('ES_HOST')}:{os.getenv('ES_PORT')}"],
            basic_auth=(os.getenv('ES_USER'), os.getenv('ES_PASSWORD'))
        )
        self.index_name = os.getenv('ES_INDEX', 'events')

    async def create_index(self):
        """Create index with appropriate mappings"""
        mapping = {
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "metadata": {"type": "object"},
                    "embedding": {"type": "dense_vector", "dims": 1536},
                    "created_at": {"type": "date"}
                }
            }
        }
        await self.client.indices.create(index=self.index_name, body=mapping)

    async def index_document(self, doc_id: str, content: str, 
                           metadata: Dict, embedding: Optional[List[float]] = None):
        """Index a document with optional embedding"""
        document = {
            "content": content,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat()
        }
        if embedding:
            document["embedding"] = embedding
            
        await self.client.index(
            index=self.index_name,
            id=doc_id,
            document=document
        )

    async def search(self, query: str, filters: Optional[Dict] = None, 
                    size: int = 10) -> List[Dict]:
        """Search documents using text query and optional filters"""
        search_body = {
            "query": {
                "bool": {
                    "must": [{
                        "match": {
                            "content": query
                        }
                    }]
                }
            },
            "size": size
        }
        
        if filters:
            search_body["query"]["bool"]["filter"] = filters

        results = await self.client.search(
            index=self.index_name,
            body=search_body
        )
        return results["hits"]["hits"]
```

### Интеграция с конвейером событий

Для интеграции с существующей системой конвейера мы добавим узел индексации Elasticsearch:

```python
class ElasticsearchIndexNode(PipelineNode):
    def __init__(self):
        self.es_client = ElasticsearchClient()

    async def process(self, event: EventSchema, context: Dict) -> Dict:
        # Index the event content
        await self.es_client.index_document(
            doc_id=str(event.id),
            content=event.payload.get("content"),
            metadata=event.metadata,
            embedding=context.get("embedding")  # Если у нас есть векторные эмбеддинги
        )
        
        return context
```

## Использование в репозитории

### 1. Добавление в Docker Compose

```yaml
elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=your_password
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
```

### 2. Environment variables

```bash
ES_HOST=elasticsearch
ES_PORT=9200
ES_USER=elastic
ES_PASSWORD=your_password
ES_INDEX=events
DATABASE_HOST=localhost
ELASTICSEARCH_URL=http://localhost:9200
```

### 3. Реализация гибридного поиска

Для продвинутого поиска, комбинирующего полнотекстовый поиск и векторное сходство:

```python
class HybridSearchService:
    def __init__(self):
        self.es_client = ElasticsearchClient()
        self.vector_store = VectorStore()

    async def hybrid_search(self, query: str, 
                          weight_text: float = 0.3,
                          weight_vector: float = 0.7) -> List[Dict]:
        """
        Perform hybrid search combining text and vector similarity
        """
        # Get vector embedding for query
        query_embedding = await self.vector_store.create_embedding_vector(query)
        
        # Elasticsearch query combining text and vector search
        search_body = {
            "query": {
                "combined_fields": {
                    "query": query,
                    "fields": ["content^2", "metadata.*"]
                }
            },
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": 10,
                "num_candidates": 100
            },
            "rank": {
                "rrf": {
                    "window_size": 10,
                    "rank_constant": 20
                }
            }
        }
        
        results = await self.es_client.client.search(
            index=self.es_client.index_name,
            body=search_body
        )
        return results["hits"]["hits"]
```

## Лучшие практики

1. **Стратегия индексации**
   - Используйте массовое индексирование для больших наборов данных
   - Реализуйте механизмы повторных попыток для неудачного индексирования
   - Учитывайте интервалы обновления для поиска, близкого к реальному времени

2. **Оптимизация запросов**
   - Используйте контекст фильтров где возможно
   - Реализуйте правильные маппинги полей
   - Учитывайте настройки анализатора поиска

3. **Мониторинг**
   - Отслеживайте производительность индексации
   - Следите за здоровьем кластера
   - Настройте оповещения об ошибках

4. **Безопасность**
   - Включите безопасность X-Pack
   - Используйте TLS для передачи данных
   - Реализуйте правильное управление доступом 