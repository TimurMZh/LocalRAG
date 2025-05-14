# Система тестирования событий

Репозиторий предоставляет комплексную систему тестирования событий, которая позволяет разработчикам тестировать конвейеры как локально, так и через API. Эта система состоит из двух основных компонентов: EventFactory для локального тестирования и утилиты send_event для тестирования API.

## Хранение событий

События хранятся в виде JSON файлов в директории `requests/events`:

```
requests/
└── events/
    ├── support_ticket.json
    ├── content_analysis.json
    └── translation_request.json
```

Пример JSON события:
```json
{
    "type": "support_ticket",
    "data": {
        "sender": "customer@example.com",
        "subject": "Login Issue",
        "body": "I can't access my account...",
        "priority": "high"
    }
}
```

## Event Factory

EventFactory предоставляет удобный способ загрузки и создания объектов событий при локальной разработке и тестировании:

```python
from utils.event_factory import EventFactory

# Create event from JSON file
event = EventFactory.create_event("support_ticket")

# Get list of available events
available_events = EventFactory.get_all_event_keys()
```

### Детали реализации

EventFactory реализует надежную систему загрузки:

```python
class EventFactory:
    @staticmethod
    def create_event(event_key: str) -> EventSchema:
        events = EventFactory._load_all_events()
        if event_key not in events:
            raise ValueError(f"Event '{event_key}.json' not found")
            
        event_data = events[event_key]
        return EventSchema(**event_data)
```

## Локальное тестирование конвейера

Вы можете использовать EventFactory для тестирования конвейеров непосредственно без использования API:

```python
# Script example
from utils.event_factory import EventFactory
from pipelines.support import SupportPipeline

def test_support_pipeline():
    # Create test event
    event = EventFactory.create_event("support_ticket")
    
    # Initialize and run pipeline
    pipeline = SupportPipeline()
    result = pipeline.run(event)
    
    # Validate results
    assert result.nodes["AnalyzeNode"]["intent"] == "account_access"
    assert result.nodes["RouterNode"]["next_node"] == "UrgentResponse"
```

## Тестирование через API с помощью send_event.py

Утилита send_event позволяет тестировать полный поток системы:

```python
# Send event through API
python requests/send_event.py support_ticket.json
```

Реализация:
```python
def send_event(event_file: str):
    """Send event to the API endpoint for processing."""
    payload = load_event(event_file)
    response = requests.post(BASE_URL, json=payload)
    
    print(f"Testing {event_file}:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
```

Результаты будут сохранены в базе данных для просмотра. Обратите внимание, что контейнеры Docker должны быть запущены для этого.

## Рабочий процесс разработки

1. **Создание тестовых событий**:
```json
// requests/events/test_event.json
{
    "type": "content_analysis",
    "data": {
        "content": "Test content...",
        "options": {
            "analyze_sentiment": true,
            "extract_keywords": true
        }
    }
}
```

2. **Локальное тестирование конвейера**:
```python
# test_pipeline.py
from utils.event_factory import EventFactory

def test_pipeline():
    # Load test event
    event = EventFactory.create_event("test_event")
    
    # Run pipeline
    pipeline = YourPipeline()
    result = pipeline.run(event)
    
    # Validate results
    print(result.nodes)
```

3. **Тестирование через API**:
```bash
# Test through API
python requests/send_event.py test_event.json
```

## Лучшие практики

### 1. Организация событий

Организуйте свои тестовые события логически:
```
requests/events/
├── support/
│   ├── basic_inquiry.json
│   └── urgent_issue.json
├── content/
│   ├── article_analysis.json
│   └── translation.json
└── validation/
    ├── edge_cases.json
    └── error_scenarios.json
```

### 2. Валидация событий

Включите валидацию в свои тестовые события:
```python
def validate_event(event: EventSchema):
    """Validate event structure and data."""
    assert event.type in VALID_EVENT_TYPES
    assert all(required in event.data for required in REQUIRED_FIELDS)
```

### 3. Покрытие тестами

Создайте события для различных сценариев:
```python
# Test different event types
for event_key in EventFactory.get_all_event_keys():
    event = EventFactory.create_event(event_key)
    result = pipeline.run(event)
    validate_result(result)
```

### 4. Советы по разработке

1. **Локальная разработка**:
```python
# Быстрое тестирование конвейера
event = EventFactory.create_event("your_test_event")
pipeline = YourPipeline()
result = pipeline.run(event)
```

2. **Валидация результатов**:
```python
# Validate pipeline results
def validate_pipeline_result(result):
    assert "AnalyzeNode" in result.nodes
    assert isinstance(result.nodes["AnalyzeNode"], dict)
    assert "confidence" in result.nodes["AnalyzeNode"]
```

Система тестирования событий предоставляет гибкий и надежный способ разработки и тестирования ваших AI конвейеров, независимо от того, работаете ли вы локально или тестируете полный поток системы через API.