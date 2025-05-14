# Основная система Pipeline

Основная система реализует сложный, но минималистичный подход к автоматизации рабочих процессов, используя направленные ациклические графы (DAGs) и паттерн Chain of Responsibility. Этот дизайн вдохновлен Make.com и подобными инструментами автоматизации рабочих процессов, но реализует эти концепции на чистом Python с фокусом на интеграцию AI.

## Фундаментальная философия

Система построена на трех ключевых принципах:

1. **Направленный ациклический поток**: Все рабочие процессы являются DAG, предотвращая бесконечные циклы и обеспечивая предсказуемые пути выполнения. Этот выбор дизайна основан на практическом опыте работы с AI системами, где циклические рабочие процессы могут привести к зацикливанию агентов.

2. **Chain of Responsibility**: Каждый шаг обработки (узел) выполняет свою конкретную задачу и передает контекст следующему узлу, поддерживая четкое разделение задач при совместном использовании состояния через структурированный объект контекста.

3. **Структурированный поток данных**: Единый, четко определенный объект `TaskContext` проходит через pipeline, обеспечивая согласованный доступ к данным и управление состоянием на всех этапах обработки.

## Основные компоненты

### Base Node (base.py)

Основой системы pipeline является класс Node, который реализует паттерн Chain of Responsibility:

```python
class Node(ABC):
    @abstractmethod
    def process(self, task_context: TaskContext) -> TaskContext:
        pass
```
Каждый узел:

- Получает контекст задачи от своего предшественника
- Выполняет свою специфическую обработку
- Обновляет контекст своими результатами
- Передает контекст своему преемнику

### Task Context (task.py)

TaskContext служит общим контейнером состояния, проходящим через pipeline:

```python
class TaskContext(BaseModel):
    event: EventSchema
    nodes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```
Этот дизайн:

- Сохраняет исходные данные события
- Хранит результаты обработки каждого узла
- Предоставляет структурированный доступ к состоянию pipeline
- Обеспечивает обмен данными между узлами

### Оркестрация Pipeline (pipeline.py)

Класс Pipeline оркеструет поток данных через узлы:

```python
class Pipeline(ABC):
    pipeline_schema: ClassVar[PipelineSchema]

    def run(self, event: EventSchema) -> TaskContext:
        task_context = TaskContext(event=event, pipeline=self)
        current_node_class = self.pipeline_schema.start
        
        while current_node_class:
            current_node = self.nodes[current_node_class]
            task_context = current_node.process(task_context)
            current_node_class = self._get_next_node_class(
                current_node_class, task_context
            )
```
Ключевые особенности:

- Проверяет структуру pipeline при инициализации
- Управляет последовательностью выполнения узлов
- Обрабатывает решения маршрутизации
- Обеспечивает обработку ошибок и логирование

### Интеграция с LLM (llm.py)

LLMNode предоставляет структурированный подход к интеграции AI моделей:

```python
class LLMNode(Node, ABC):
    class ContextModel(BaseModel):
        pass

    class ResponseModel(BaseModel):
        pass

    @abstractmethod
    def create_completion(self, context: ContextModel) -> ResponseModel:
        pass

    @abstractmethod
    def get_context(self, task_context: TaskContext) -> ContextModel:
        pass
```
Этот дизайн:

- Обеспечивает структурированный ввод/вывод через Pydantic модели
- Разделяет подготовку контекста и взаимодействие с моделью
- Обеспечивает типобезопасную обработку ответов
- Упрощает интеграцию с библиотекой instructor для структурированного вывода

### Логика маршрутизации (router.py)

Система маршрутизации обеспечивает условные пути выполнения:

```python
class BaseRouter(Node):
    def route(self, task_context: TaskContext) -> Node:
        for route_node in self.routes:
            next_node = route_node.determine_next_node(task_context)
            if next_node:
                return next_node
        return self.fallback
```
Особенности:

- Условное ветвление на основе контекста задачи
- Поддержка множественных правил маршрутизации 
- Обработка fallback сценариев
- Четкое отслеживание решений маршрутизации

### Схема Pipeline (schema.py)

Система схем определяет структуру pipeline с использованием Pydantic моделей:

```python
class PipelineSchema(BaseModel):
    description: Optional[str]
    start: Type[Node]
    nodes: List[NodeConfig]
```
Преимущества:

- Типобезопасное определение pipeline
- Самодокументируемая структура 
- Валидация во время конструирования
- Четкая визуализация потока

### Валидация (validate.py)

Система валидации обеспечивает целостность pipeline:

```python
class PipelineValidator:
    def validate(self):
        self._validate_dag()
        self._validate_connections()
```
Проверки:

- Структура DAG (отсутствие циклов)
- Достижимость узлов
- Корректность конфигурации маршрутизации 
- Согласованность соединений

## Шаблоны проектирования в действии

### Цепочка обязанностей

Шаблон проявляется несколькими способами:

1. Каждый узел обрабатывает свою конкретную задачу независимо
2. Узлы взаимодействуют только через TaskContext
3. Поток обработки однонаправленный
4. Каждый узел решает, передавать ли управление дальше

### Фабричный шаблон

Используется при создании экземпляров узлов:
```python
def _instantiate_node(node_class: Type[Node]) -> Node:
    return node_class()
```

### Стратегия

Реализована в маршрутизаторах:
```python
class RouterNode(ABC):
    @abstractmethod
    def determine_next_node(self, task_context: TaskContext) -> Optional[Node]:
        pass
```

## Практическое использование

Создание pipeline включает:

1. Определение узлов для каждого шага обработки:
```python
class AnalyzeNode(Node):
    def process(self, context: TaskContext) -> TaskContext:
        # Implement analysis logic
        return context
```

2. Определение структуры pipeline:
```python
class AnalysisPipeline(Pipeline):
    pipeline_schema = PipelineSchema(
        start=AnalyzeNode,
        nodes=[
            NodeConfig(node=AnalyzeNode, connections=[ResultNode])
        ]
    )
```

3. Выполнение pipeline:
```python
pipeline = AnalysisPipeline()
result = pipeline.run(event)
```

Этот дизайн обеспечивает надежную основу для создания сложных рабочих процессов AI, сохраняя ясность кода и предотвращая типичные ошибки в проектировании систем AI.