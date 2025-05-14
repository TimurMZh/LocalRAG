# Дизайн и реализация Pipeline

Система pipeline в Репозитории предоставляет структурированный способ реализации AI рабочих процессов. Это руководство объясняет, как проектировать, реализовывать и регистрировать pipeline для обработки через систему Celery worker.

## Архитектура Pipeline

### Система Registry (registry.py)

PipelineRegistry действует как центральный хаб для управления различными реализациями pipeline:

```python
class PipelineRegistry:
    pipelines: Dict[str, Type[Pipeline]] = {
        "support": CustomerSupportPipeline,
        "content": ContentAnalysisPipeline,
    }

    @staticmethod
    def get_pipeline_type(event: EventSchema) -> str:
        # Implement your routing logic
        if "support" in event.data.get("type"):
            return "support"
        return "content"
```
Этот реестр:

- Сопоставляет типы событий с конкретными реализациями pipeline
- Обеспечивает динамический выбор pipeline на основе атрибутов события
- Позволяет легко добавлять новые типы pipeline

## Создание Pipeline

### Базовая структура Pipeline

Типичный pipeline состоит из нескольких узлов, организованных в направленный ациклический граф (DAG):

```python
class ContentAnalysisPipeline(Pipeline):
    pipeline_schema = PipelineSchema(
        description="Analyzes content using AI",
        start=ExtractNode,
        nodes=[
            NodeConfig(node=ExtractNode, connections=[AnalyzeNode]),
            NodeConfig(node=AnalyzeNode, connections=[RouterNode]),
            NodeConfig(
                node=RouterNode, 
                connections=[SummarizeNode, TranslateNode],
                is_router=True
            ),
            NodeConfig(node=SummarizeNode, connections=[FormatNode]),
            NodeConfig(node=TranslateNode, connections=[FormatNode]),
            NodeConfig(node=FormatNode, connections=[])
        ]
    )
```

### Типы узлов и их реализация

1. **Базовый узел обработки**:
```python
class ExtractNode(Node):
    def process(self, context: TaskContext) -> TaskContext:
        # Extract text from input
        text = context.event.data.get("content")
        context.nodes[self.node_name] = {"extracted_text": text}
        return context
```

2. **LLM Узел**:
```python
class AnalyzeNode(LLMNode):
    class ContextModel(BaseModel):
        text: str
        analysis_type: str

    class ResponseModel(BaseModel):
        sentiment: str
        key_points: List[str]

    def get_context(self, task_context: TaskContext) -> ContextModel:
        return self.ContextModel(
            text=task_context.nodes["ExtractNode"]["extracted_text"],
            analysis_type=task_context.event.data.get("analysis_type")
        )

    def create_completion(self, context: ContextModel) -> ResponseModel:
        llm = LLMFactory("openai")
        prompt = PromptManager.get_prompt(
            "extract",
            pipeline="support",
        )
        return llm.create_completion(
            response_model=self.ResponseModel,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": f"# New data:\n{context.model_dump()}",
                },
            ],
        )

    def process(self, task_context: TaskContext) -> TaskContext:
        context = self.get_context(task_context)
        response = self.create_completion(context)
        task_context.nodes[self.node_name] = response
        return task_context
```

3. **Router Узел**:
```python
class ContentRouter(BaseRouter):
    def __init__(self):
        self.routes = [
            SummaryRoute(),
            TranslationRoute()
        ]
        self.fallback = SummaryRoute()

class SummaryRoute(RouterNode):
    def determine_next_node(self, context: TaskContext) -> Optional[Node]:
        if context.event.data.get("action") == "summarize":
            return SummarizeNode()
        return None
```

## Интеграция с Celery

Celery worker (tasks.py) обрабатывает выполнение pipeline:

```python
@celery_app.task(name="process_incoming_event")
def process_incoming_event(event_id: str):
    with db_session() as session:
        # Get event from database
        event = repository.get(id=event_id)
        
        # Determine and execute pipeline
        pipeline = PipelineRegistry.get_pipeline(event)
        result = pipeline.run(event)
        
        # Store results
        event.task_context = result.model_dump()
        repository.update(event)
```

## Лучшие практики проектирования Pipeline

### 1. Granularity узлов

Создавайте узлы с одной ответственностью:
```python
# Good: Focused node
class SentimentNode(LLMNode):
    def process(self, context: TaskContext) -> TaskContext:
        # Only handles sentiment analysis
        return context

# Avoid: Too many responsibilities
class AnalysisNode(LLMNode):
    def process(self, context: TaskContext) -> TaskContext:
        # Handles sentiment, entities, translation, etc.
        return context
```

### 2. Data Flow

Сохраняйте четкое управление зависимостями:
```python
class SummarizeNode(LLMNode):
    def get_context(self, task_context: TaskContext) -> ContextModel:
        # Clearly specify data requirements
        return self.ContextModel(
            text=task_context.nodes["ExtractNode"]["text"],
            style=task_context.nodes["AnalyzeNode"]["tone"]
        )
```

### 3. Размещение Router

Размещайте маршрутизаторы в точках принятия решений:
```python
pipeline_schema = PipelineSchema(
    start=ValidateNode,
    nodes=[
        NodeConfig(node=ValidateNode, connections=[RouterNode]),
        NodeConfig(
            node=RouterNode,
            connections=[ProcessA, ProcessB],
            is_router=True
        )
    ]
)
```

### 4. Обработка ошибок

Реализуйте надежную обработку ошибок:

```python
class ProcessingNode(Node):
    def process(self, context: TaskContext) -> TaskContext:
        try:
            result = self.process_data(context)
            context.nodes[self.node_name] = {"status": "success", "data": result}
        except Exception as e:
            context.nodes[self.node_name] = {
                "status": "error",
                "error": str(e)
            }
        return context
```

## Организация Pipeline

Организуйте ваш каталог pipelines:
```
pipelines/
├── __init__.py
├── registry.py
├── support/
│   ├── __init__.py
│   ├── nodes.py
│   └── pipeline.py
└── content/
    ├── __init__.py
    ├── nodes.py
    └── pipeline.py
```

## Тестировочный Pipeline

Создайте комплексные тесты:
```python
def test_content_pipeline():
    # Create test event
    event = EventSchema(type="content_analysis", data={...})
    
    # Initialize pipeline
    pipeline = ContentAnalysisPipeline()
    
    # Run pipeline
    result = pipeline.run(event)
    
    # Assert expected results
    assert "AnalyzeNode" in result.nodes
    assert result.nodes["AnalyzeNode"]["sentiment"] == "positive"
```

Помните, что хорошо спроектированные pipeline:

- Легко понять
- Поддерживаемы
- Тестируемы
- Переиспользуемы
- Устойчивы к ошибкам

Система pipeline предоставляет структуру - ваша реализация предоставляет интеллект.

## Стратегия Pipeline: Single vs. Multiple

### Когда использовать один Pipeline

Один pipeline часто достаточен, когда:

1. **Common Processing Flow**: Ваше приложение обрабатывает вариации одного и того же базового рабочего процесса:
```python
class ContentPipeline(Pipeline):
    pipeline_schema = PipelineSchema(
        start=ValidateNode,
        nodes=[
            NodeConfig(node=ValidateNode, connections=[RouterNode]),
            NodeConfig(
                node=RouterNode, 
                connections=[
                    TextAnalysisNode,
                    ImageAnalysisNode,
                    AudioAnalysisNode
                ],
                is_router=True
            ),
            # All paths converge to common processing
            NodeConfig(node=TextAnalysisNode, connections=[EnrichmentNode]),
            NodeConfig(node=ImageAnalysisNode, connections=[EnrichmentNode]),
            NodeConfig(node=AudioAnalysisNode, connections=[EnrichmentNode]),
            NodeConfig(node=EnrichmentNode, connections=[StorageNode]),
        ]
    )
```

2. **Branching Logic**: Когда различия могут быть обработаны через маршрутизацию:
```python
class RouterNode(BaseRouter):
    def determine_next_node(self, context: TaskContext) -> Node:
        content_type = context.event.data.get("type")
        return {
            "text": TextAnalysisNode(),
            "image": ImageAnalysisNode(),
            "audio": AudioAnalysisNode()
        }.get(content_type, TextAnalysisNode())
```

3. **Shared Context**: Когда разные процессы нуждаются в доступе к одному и тому же контексту:
```python
class EnrichmentNode(Node):
    def process(self, context: TaskContext) -> TaskContext:
        # Access results from any previous node
        analysis_results = context.nodes.get(
            f"{context.metadata['analysis_type']}AnalysisNode"
        )
        # Enrich with common logic
        return context
```

### Когда использовать несколько Pipeline

Рассмотрите вариант использования несколько pipeline, когда:

1. **Разные бизнес-домены**:
```python
class CustomerSupportPipeline(Pipeline):
    # Handle customer inquiries
    pipeline_schema = PipelineSchema(...)

class ContentModerationPipeline(Pipeline):
    # Handle content moderation
    pipeline_schema = PipelineSchema(...)
```

2. **Разные требования к безопасности**:
```python
class PublicPipeline(Pipeline):
    # Public-facing processing
    pipeline_schema = PipelineSchema(...)

class InternalPipeline(Pipeline):
    # Internal, privileged processing
    pipeline_schema = PipelineSchema(...)
```

3. **Совершенно разные рабочие процессы**:
```python
class DocumentProcessingPipeline(Pipeline):
    # Document-specific workflow
    pipeline_schema = PipelineSchema(
        nodes=[
            NodeConfig(node=OCRNode),
            NodeConfig(node=ClassificationNode),
            # ...
        ]
    )

class ChatPipeline(Pipeline):
    # Conversational workflow
    pipeline_schema = PipelineSchema(
        nodes=[
            NodeConfig(node=ContextNode),
            NodeConfig(node=ResponseNode),
            # ...
        ]
    )
```

### Гибридный подход

Вы можете также использовать гибридный подход, когда у вас несколько pipeline, которые разделяют общие компоненты:

```python
# Shared nodes module
class CommonNodes:
    class ValidationNode(Node):
        def process(self, context: TaskContext) -> TaskContext:
            # Common validation logic
            return context

# Multiple pipelines using shared components
class Pipeline1(Pipeline):
    pipeline_schema = PipelineSchema(
        start=CommonNodes.ValidationNode,
        nodes=[
            NodeConfig(node=CommonNodes.ValidationNode),
            NodeConfig(node=CustomNode1)
        ]
    )

class Pipeline2(Pipeline):
    pipeline_schema = PipelineSchema(
        start=CommonNodes.ValidationNode,
        nodes=[
            NodeConfig(node=CommonNodes.ValidationNode),
            NodeConfig(node=CustomNode2)
        ]
    )
```

### Фреймворк принятия решений

При принятии решения о структуре pipeline, рассмотрите:

1. **Управление сложностью**:
   - Single Pipeline: Когда вариации минимальны
   - Multiple Pipelines: Когда сложность становится трудно управляемой в одном pipeline

2. **Обслуживание**:
   - Single Pipeline: Проще поддерживать, когда логика связана
   - Multiple Pipelines: Лучше, когда разные команды управляют разными рабочими процессами

3. **Производительность**:
   - Single Pipeline: Можно оптимизировать общие ресурсы
   - Multiple Pipelines: Можно масштабировать разные рабочие процессы независимо

4. **Безопасность**:
   - Single Pipeline: Когда контекст безопасности единообразен
   - Multiple Pipelines: Когда требуются разные контексты безопасности

Помните: Начинайте с одного pipeline и разделяйте только при необходимости. Проще разделить pipeline позже, чем объединить несколько pipeline.