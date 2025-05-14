from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ElasticsearchDocument(BaseModel):
    """Base model for Elasticsearch documents"""

    content: str = Field(..., description="Main content of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
