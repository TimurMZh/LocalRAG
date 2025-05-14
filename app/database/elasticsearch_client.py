from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Optional
import os
from functools import lru_cache


class ElasticsearchClient:
    def __init__(self):
        # Add default values for Elasticsearch connection
        elasticsearch_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")

        self.client = AsyncElasticsearch(hosts=[elasticsearch_url], basic_auth=("elastic", "your_password"))
        self.index_name = os.getenv("ELASTICSEARCH_INDEX", "events")

    async def close(self):
        """Close the Elasticsearch client connection"""
        await self.client.close()

    async def init(self):
        """Initialize index with mappings"""
        if not await self.client.indices.exists(index=self.index_name):
            await self.create_index()

    async def create_index(self):
        """Create index with appropriate mappings"""
        mapping = {
            "mappings": {
                "properties": {
                    "content": {"type": "text", "analyzer": "standard"},
                    "metadata": {"type": "object", "dynamic": True},
                    "embedding": {"type": "dense_vector", "dims": 1536, "index": True, "similarity": "cosine"},
                    "created_at": {"type": "date"},
                }
            },
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1}},
        }
        await self.client.indices.create(index=self.index_name, body=mapping)

    async def index_document(self, doc_id: str, document: Dict):
        """Index a document"""
        await self.client.index(index=self.index_name, id=doc_id, document=document, refresh=True)

    async def search(self, query: str, filters: Optional[Dict] = None, size: int = 10) -> List[Dict]:
        """Basic text search"""
        search_body = {"query": {"bool": {"must": [{"match": {"content": query}}]}}, "size": size}

        if filters:
            search_body["query"]["bool"]["filter"] = filters

        results = await self.client.search(index=self.index_name, body=search_body)
        return results["hits"]["hits"]

    async def vector_search(self, vector: List[float], size: int = 10) -> List[Dict]:
        """Vector similarity search"""
        search_body = {
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": vector},
                    },
                }
            },
            "size": size,
        }

        results = await self.client.search(index=self.index_name, body=search_body)
        return results["hits"]["hits"]


@lru_cache()
def get_elasticsearch_client() -> ElasticsearchClient:
    return ElasticsearchClient()
