# API Layer Documentation

The API layer in the Repository serves as the main entry point for all event-driven operations. Built on FastAPI, this layer transforms incoming HTTP requests into events that flow through the system's event-driven architecture.

## Architectural Overview

The API layer implements the "receive-and-delegate" pattern, where requests are quickly validated, stored, and delegated to background handlers. This design ensures high availability and responsiveness, as the API immediately acknowledges valid requests without waiting for complete processing.

When a request arrives, it goes through the following stages:

1. FastAPI validates the incoming payload against defined schemas
2. The validated event is stored in PostgreSQL
3. A background task is queued via Celery
4. The API returns a 202 Accepted response with the task identifier

## Core Components

### Dependencies (dependencies.py)

The dependencies module provides core services for API endpoints through FastAPI's dependency injection system. The primary dependency is the database session manager, which ensures proper database connection handling:

```python
def db_session() -> Generator:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ex
    finally:
        session.close()
```
This pattern ensures proper database session management regardless of request success or failure.

### Event Schema (event_schema.py)

Event schemas define the contract between API clients and the system. Using Pydantic models, we ensure strict validation of incoming requests before they enter the processing pipeline. The schema system is extensible, allowing custom validation rules for different event types.

#### Pydantic Model Integration

Pydantic models serve as the foundation for data validation and serialization. These models provide:

- Runtime type checking and validation
- JSON schema generation for OpenAPI documentation
- Automatic serialization/deserialization of complex data types

Example of a typical event schema:

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class EventSchema(BaseModel):
    event_type: str = Field(..., description="Type of event being processed")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Optional metadata")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "event_type": "document_processing",
                "payload": {"document_id": "123", "action": "analyze"},
                "metadata": {"priority": "high"}
            }]
        }
    }
```
For more information about Pydantic models and their capabilities, refer to:
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Pydantic Guide](https://fastapi.tiangolo.com/tutorial/body/#using-pydantic-models)

### Endpoints (endpoint.py)

The endpoints module implements the basic event handling logic. It follows REST principles and implements the "accept-and-delegate" pattern:

```python
@router.post("/")
def handle_event(
    data: EventSchema,
    session: Session = Depends(db_session),
) -> Response:
    # Store event
    event = Event(data=data.model_dump(mode="json"))
    repository.create(obj=event)

    # Queue for processing
    task_id = celery_app.send_task(
        "process_incoming_event",
        args=[str(event.id)],
    )

    return Response(
        status_code=HTTPStatus.ACCEPTED
    )
```

### Router Configuration (router.py)

The router module organizes endpoints into logical groups and applies common configurations. This modular approach makes it easy to add new endpoints while maintaining consistent routing patterns.

## Integration Points

The API layer integrates with several other system components:

### Database Integration
Through the repository pattern, the API layer stores events while maintaining separation of concerns. Database operations are abstracted behind repository interfaces, making the system flexible to database changes.

### Task Queue Integration
The API layer queues tasks for background processing using Celery. This integration point is critical for the event-driven nature of the system, allowing asynchronous processing of potentially long-running operations.

### Validation Integration
The FastAPI validation system works together with Pydantic models to ensure data integrity before events enter the processing pipeline.

## Extending the API

To add new endpoints, follow these steps:

1. Define new schemas in event_schema.py
2. Create endpoint handlers in endpoint.py
3. Update router configuration if needed
4. Implement corresponding pipeline handlers

The modular design makes API extension straightforward while maintaining consistency and reliability.
