# Elasticsearch Integration

The Elasticsearch integration provides powerful full-text search capabilities and analytics for the application. It enables efficient indexing and searching of documents, events, and other data types.

## Architecture Overview

The system consists of three main components:

1. **Index Manager**: Handles index creation and management
2. **Document Service**: Manages document indexing and retrieval
3. **Search Service**: Provides search functionality

## Index Management

The IndexManager class handles index creation and configuration:

```python
class IndexManager:
    def __init__(self, client: Elasticsearch):
        self.client = client

    def create_index(self, index_name: str, settings: Dict[str, Any]) -> None:
        """
        Create a new index with specified settings.
        
        Args:
            index_name: Name of the index to create
            settings: Index settings and mappings
        """
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(
                index=index_name,
                body=settings
            )

    def get_index_settings(self, index_name: str) -> Dict[str, Any]:
        """
        Get current index settings.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Dictionary containing index settings
        """
        return self.client.indices.get_settings(index=index_name)
```

## Document Service

The DocumentService handles document indexing and retrieval:

```python
class DocumentService:
    def __init__(self, client: Elasticsearch):
        self.client = client

    def index_document(
        self,
        index_name: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index a document in Elasticsearch.
        
        Args:
            index_name: Target index name
            document: Document to index
            doc_id: Optional document ID
            
        Returns:
            Indexing response
        """
        return self.client.index(
            index=index_name,
            body=document,
            id=doc_id
        )

    def get_document(
        self,
        index_name: str,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a document by ID.
        
        Args:
            index_name: Index name
            doc_id: Document ID
            
        Returns:
            Retrieved document
        """
        return self.client.get(
            index=index_name,
            id=doc_id
        )
```

## Search Service

The SearchService provides search functionality:

```python
class SearchService:
    def __init__(self, client: Elasticsearch):
        self.client = client

    def search(
        self,
        index_name: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0
    ) -> Dict[str, Any]:
        """
        Execute a search query.
        
        Args:
            index_name: Target index name
            query: Search query
            size: Number of results to return
            from_: Starting offset
            
        Returns:
            Search results
        """
        return self.client.search(
            index=index_name,
            body={
                "query": query,
                "size": size,
                "from": from_
            }
        )

    def count(
        self,
        index_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Count documents matching a query.
        
        Args:
            index_name: Target index name
            query: Search query
            
        Returns:
            Number of matching documents
        """
        return self.client.count(
            index=index_name,
            body={"query": query}
        )["count"]
```

## Index Settings

Example index settings for different use cases:

```python
# Event index settings
EVENT_INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "custom_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "event_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "type": {"type": "keyword"},
            "content": {
                "type": "text",
                "analyzer": "custom_analyzer"
            },
            "metadata": {"type": "object"}
        }
    }
}

# Document index settings
DOCUMENT_INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1
    },
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "english"
            },
            "content": {
                "type": "text",
                "analyzer": "english"
            },
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "tags": {"type": "keyword"}
        }
    }
}
```

## Usage Examples

### Indexing Events

```python
# Initialize services
es_client = Elasticsearch(["http://localhost:9200"])
index_manager = IndexManager(es_client)
document_service = DocumentService(es_client)

# Create event index
index_manager.create_index("events", EVENT_INDEX_SETTINGS)

# Index an event
event = {
    "event_id": "evt_123",
    "timestamp": "2024-03-20T10:00:00Z",
    "type": "user_action",
    "content": "User clicked submit button",
    "metadata": {
        "user_id": "user_456",
        "action": "submit"
    }
}

document_service.index_document("events", event, doc_id=event["event_id"])
```

### Searching Events

```python
# Initialize search service
search_service = SearchService(es_client)

# Search for events
query = {
    "bool": {
        "must": [
            {"match": {"type": "user_action"}},
            {"range": {
                "timestamp": {
                    "gte": "2024-03-20T00:00:00Z",
                    "lte": "2024-03-20T23:59:59Z"
                }
            }}
        ]
    }
}

results = search_service.search("events", query)
```

## Best Practices

1. **Index Design**
   - Use appropriate number of shards
   - Configure replicas for high availability
   - Choose suitable analyzers for text fields

2. **Query Optimization**
   - Use filter context when possible
   - Implement pagination for large result sets
   - Cache frequently used queries

3. **Performance**
   - Bulk index operations when possible
   - Monitor index size and growth
   - Regular index maintenance

4. **Security**
   - Secure Elasticsearch cluster
   - Implement access control
   - Encrypt sensitive data

## Configuration

Elasticsearch settings can be configured through environment variables:

```python
# config/elasticsearch_config.py
class ElasticsearchSettings:
    hosts: List[str] = ["http://localhost:9200"]
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False
    verify_certs: bool = True
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True
```

This allows for flexible configuration while maintaining security and performance. 