from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field

"""
Event Schema Module

This module defines the Pydantic models that FastAPI uses to validate incoming
HTTP requests. It specifies the expected structure and validation rules for
events entering the system through the API endpoints.
"""


class EventSchema(BaseModel):
    """Schema template for incoming event requests.

    This is an example schema for a support ticket system. You should:

    1. Modify the fields to match your event structure
    2. Adjust validation rules for your requirements
    3. Update examples to reflect your use case
    4. Add any additional fields needed

    Current Example (Support Ticket):
    """

    ticket_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the ticket"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time when the ticket was created",
    )
    from_email: EmailStr = Field(..., description="Email address of the sender")
    to_email: EmailStr = Field(..., description="Email address of the recipient")
    sender: str = Field(..., description="Name or identifier of the sender")
    subject: str = Field(..., description="Subject of the ticket")
    body: str = Field(..., description="The body of the ticket")

