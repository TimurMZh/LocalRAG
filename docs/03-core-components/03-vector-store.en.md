# Vector Store

## Understanding Vectors in AI Systems

Vector embeddings are numerical representations of data (text, images, etc.) that capture semantic meaning in multi-dimensional space. These embeddings enable:

- Semantic search capabilities
- Similarity comparison
- Efficient information retrieval
- Context-aware AI operations

## Why PostgreSQL?

Using PostgreSQL with pgvectorscale as a vector database offers several key advantages over specialized vector databases:

- PostgreSQL is a robust open-source database with a rich ecosystem of tools, drivers, and connectors. This ensures transparency, community support, and continuous improvements.

- By using PostgreSQL, you can manage both relational and vector data in a single database. This reduces operational complexity as there's no need to maintain and synchronize multiple databases.

- Pgvectorscale extends pgvector capabilities, providing faster search, higher accuracy, and efficient time-based filtering. It uses advanced indexing techniques, such as DiskANN-based indexing, to significantly speed up nearest neighbor (ANN) search.

Pgvectorscale Vector is built on top of [pgvector](https://github.com/pgvector/pgvector), offering enhanced performance and additional features, making PostgreSQL a powerful and versatile choice for AI applications.

## Current Implementation

Our PostgreSQL vector implementation uses the TimescaleDB vector extension:

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

## Extending or Replacing Vector Store

The vector store implementation is designed for replaceability. You can implement your own vector store by following these steps:

1. Create a new vector store class:
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

2. Update configuration:
```python
# config/database_config.py
class VectorStoreConfig(BaseSettings):
    provider: str = "custom"  # or "postgres", "pinecone", etc.
    # Additional provider-specific settings
```

### Popular Alternatives

You can consider these alternatives depending on your needs:
1. **Pinecone**
   - Specialized vector database
   - Managed service
   - High performance
   - Built-in scaling

2. **Weaviate**
   - Multimodal vectors
   - Rich query capabilities
   - GraphQL interface
   - Self-hosting option

3. **Qdrant**
   - Rust-based performance
   - Rich filtering
   - Simple deployment
   - Active development

## Performance Considerations

When using PostgreSQL for vectors:

1. **Indexing**
   - Use appropriate index types (IVFFlat, HNSW)
   - Configure index parameters based on data size
   - Regular index maintenance

2. **Partitioning**
   - TimescaleDB hypertables for time-based partitioning
   - Partition by metadata attributes when needed
   - Balance partition sizes 