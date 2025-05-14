# System Architecture Diagrams

This document provides a comprehensive overview of the system architecture through various diagrams.

## System Components

```mermaid
graph TB
    Client[Client] --> API[API Layer]
    API --> DB[(Database)]
    API --> Redis[(Redis)]
    Redis --> Worker[Celery Worker]
    Worker --> Pipeline[Pipeline System]
    Pipeline --> LLM[LLM Integration]
    Pipeline --> VectorStore[Vector Store]
    Pipeline --> Elasticsearch[Elasticsearch]
```

## Event Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    participant Redis
    participant Worker
    participant Pipeline
    participant LLM
    participant VectorStore
    participant Elasticsearch

    Client->>API: POST /events
    API->>DB: Store Event
    API->>Redis: Queue Task
    API->>Client: 202 Accepted
    
    Worker->>Redis: Poll for Tasks
    Worker->>DB: Get Event
    Worker->>Pipeline: Process Event
    
    Pipeline->>LLM: Generate Response
    Pipeline->>VectorStore: Store Embeddings
    Pipeline->>Elasticsearch: Index Content
    
    Pipeline->>Worker: Return Results
    Worker->>DB: Store Results
```

## Pipeline Architecture

```mermaid
graph LR
    Input[Input Node] --> Router[Router Node]
    Router --> Node1[Processing Node 1]
    Router --> Node2[Processing Node 2]
    Node1 --> Output[Output Node]
    Node2 --> Output
```

## Data Flow

```mermaid
graph TB
    Event[Event] --> Pipeline[Pipeline]
    Pipeline --> Context[Task Context]
    Context --> Result[Result]
    Result --> DB[(Database)]
    Result --> VectorStore[(Vector Store)]
    Result --> Elasticsearch[(Elasticsearch)]
```

## Component Dependencies

```mermaid
graph TB
    API[API Layer] --> DB[(Database)]
    API --> Redis[(Redis)]
    Worker[Celery Worker] --> Redis
    Worker --> Pipeline[Pipeline System]
    Pipeline --> LLM[LLM Integration]
    Pipeline --> VectorStore[Vector Store]
    Pipeline --> Elasticsearch[Elasticsearch]
    DB --> VectorStore
    DB --> Elasticsearch
```

## Deployment Architecture

```mermaid
graph TB
    Client[Client] --> LB[Load Balancer]
    LB --> API1[API Instance 1]
    LB --> API2[API Instance 2]
    API1 --> Redis[(Redis)]
    API2 --> Redis
    Redis --> Worker1[Worker 1]
    Redis --> Worker2[Worker 2]
    Worker1 --> DB[(Database)]
    Worker2 --> DB
    DB --> VectorStore[(Vector Store)]
    DB --> Elasticsearch[(Elasticsearch)]
``` 