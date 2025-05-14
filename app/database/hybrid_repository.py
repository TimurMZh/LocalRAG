from typing import List, Dict, Optional
from .elasticsearch_client import get_elasticsearch_client
from .repository import GenericRepository
from .event import Event
from sqlalchemy.orm import Session


class HybridSearchRepository:
    def __init__(self, session: Session):
        self.es_client = get_elasticsearch_client()
        self.event_repository = GenericRepository(session=session, model=Event)

    async def index_event(self, event: Event, embedding: Optional[List[float]] = None):
        """Index an event in both PostgreSQL and Elasticsearch"""
        # Store in PostgreSQL
        db_event = self.event_repository.create(event)

        # Ensure we have a valid string representation of the UUID
        doc_id = str(db_event.id)  # This will be a proper UUID string

        # Prepare document for Elasticsearch
        document = {
            "content": event.data.get("content", ""),
            "metadata": event.data.get("metadata", {}),
            "created_at": event.created_at.isoformat(),
        }
        if embedding:
            document["embedding"] = embedding

        # Index in Elasticsearch
        await self.es_client.index_document(doc_id=doc_id, document=document)

        return db_event

    async def hybrid_search(
        self,
        query: str,
        query_vector: List[float],
        weight_text: float = 0.3,
        weight_vector: float = 0.7,
        size: int = 10,
        return_raw_es: bool = False,
    ) -> List[Dict]:
        """
        Perform hybrid search combining text and vector similarity
        """
        search_body = {
            "query": {
                "script_score": {
                    "query": {"match": {"content": {"query": query}}},
                    "script": {
                        "source": f"(cosineSimilarity(params.query_vector, 'embedding') + 1.0) * {weight_vector} + _score * {weight_text}",
                        "params": {"query_vector": query_vector},
                    },
                }
            },
            "size": size,
        }

        results = await self.es_client.client.search(index=self.es_client.index_name, body=search_body)

        # Return raw Elasticsearch results if requested
        if return_raw_es:
            return results["hits"]["hits"]

        # Add debug logging
        if not results["hits"]["hits"]:
            print(f"ES Debug - Total hits: {results['hits']['total']['value']}")
            print(f"ES Debug - Query body: {search_body}")
            return []

        try:
            # Get full events from PostgreSQL
            events = []
            for hit in results["hits"]["hits"]:
                try:
                    # Convert numeric ID to UUID format if necessary
                    event_id = hit["_id"]
                    if event_id.isdigit():
                        from uuid import UUID

                        # Create a deterministic UUID from the numeric ID
                        event_id = str(UUID(int=int(event_id), version=4))

                    event = self.event_repository.get(id=event_id)
                    if event:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: Could not process result with ID {hit['_id']}: {str(e)}")
                    continue
            return events
        except Exception as e:
            print(f"Error retrieving events from database: {str(e)}")
            self.event_repository.session.rollback()
            return []
