# Управление промптами

Репозиторий использует систему управления промптами, основанную на шаблонизаторе Jinja2 и метаданных frontmatter. Такой подход обеспечивает четкое разделение между логикой промптов и их содержимым, предоставляя при этом мощные возможности шаблонизации.

## Почему Jinja Templates?

Мы выбрали шаблонизатор Jinja по нескольким ключевым причинам:

1. **Динамический контент**: Мощные возможности шаблонизации Jinja позволяют:
   - Создавать условные секции промптов
   - Генерировать контент на основе циклов
   - Интерполировать переменные
   - Наследовать и переиспользовать шаблоны

2. **Разделение ответственности**: Шаблоны разделяют:
   - Структуру промпта (шаблон)
   - Динамический контент (переменные)
   - Метаданные (frontmatter)

3. **Валидация и типобезопасность**: При использовании с Pydantic моделями:
   - Переменные шаблонов могут быть валидированы
   - Type hints обеспечивают лучшую поддержку IDE
   - Валидация во время выполнения гарантирует корректность данных

## Структура промптов

Промпты хранятся как файлы `.j2` с метаданными frontmatter:

```yaml
---
name: ticket_analysis
description: Analyzes customer support tickets for intent and urgency
author: AI Team
version: 1.0
---
You are a customer support analyst. Analyze the following ticket:

Sender: {{ sender }}
Subject: {{ subject }}

Content:
{{ body }}

Provide a structured analysis including:
1. Customer intent
2. Urgency level
3. Required actions

{% if context %}
Consider this additional context:
{% for item in context %}
- {{ item }}
{% endfor %}
{% endif %}
```

## Использование Prompt Manager

### Основное использование

```python
from services.prompt_loader import PromptManager

# Load and render a prompt
prompt = PromptManager.get_prompt(
    "ticket_analysis",
    sender="customer@example.com",
    subject="Urgent: Login Issue",
    body="Cannot access my account...",
    context=["Previous ticket: Password reset requested"]
)
```

### Получение информации о шаблоне

```python
# Get template metadata and requirements
info = PromptManager.get_template_info("ticket_analysis")
print(info)
# {
#     "name": "ticket_analysis",
#     "description": "Analyzes customer support tickets...",
#     "author": "AI Team",
#     "variables": ["sender", "subject", "body", "context"],
#     "frontmatter": {...}
# }
```

## Интеграция с LLM узлами

Система управления промптами интегрируется с LLM узлами:

```python
class AnalyzeTicket(LLMNode):
    def create_completion(self, context: ContextModel) -> ResponseModel:
        # Load prompt template
        prompt = PromptManager.get_prompt(
            "ticket_analysis",
            pipeline="support",
            sender=context.sender,
            subject=context.subject,
            body=context.body
        )
        
        # Use in LLM completion
        return self.llm.create_completion(
            response_model=self.ResponseModel,
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
```

## Организация промптов

Промпты организованы в структуру каталогов:

```
app/
└── prompts/
    ├── support/
    │   ├── ticket_analysis.j2
    │   └── response_template.j2
    ├── content/
    │   ├── summarize.j2
    │   └── analyze.j2
    └── shared/
        └── common_instructions.j2
```

## Расширенные функции

### Наследование шаблонов

```jinja
{# base_prompt.j2 #}
{% block system_instruction %}{% endblock %}

{% block content %}{% endblock %}

{% block response_format %}{% endblock %}

{# specific_prompt.j2 #}
{% extends "base_prompt.j2" %}

{% block system_instruction %}
You are an AI assistant specialized in...
{% endblock %}

{% block content %}
Analyze the following: {{ content }}
{% endblock %}
```

### Условная логика

```jinja
{% if confidence_required %}
Please provide confidence scores for each analysis point.
{% endif %}

{% if language != "english" %}
Respond in {{ language }}.
{% endif %}
```

### Циклы и структуры данных

```jinja
Consider the following context:
{% for item in context_items %}
{{ loop.index }}. {{ item.title }}
   - Relevance: {{ item.relevance }}
   - Source: {{ item.source }}
{% endfor %}
```
## Лучшие практики

1. **Контроль версий**:
   - Храните промпты в системе контроля версий
   - Используйте frontmatter для метаданных версионирования
   - Документируйте изменения в файлах промптов

2. **Организация шаблонов**:
   - Группируйте связанные промпты в поддиректории
   - Используйте четкие, описательные имена файлов
   - Включайте примеры использования в frontmatter

3. **Управление переменными**:
   - Документируйте необходимые переменные
   - Предоставляйте значения по умолчанию, где это уместно
   - Используйте type hints в документации

4. **Обработка ошибок**:
   ```python
   try:
       prompt = PromptManager.get_prompt("template_name", **vars)
   except TemplateError as e:
       logger.error(f"Template error: {e}")
       # Handle gracefully
   ```
## Соображения безопасности

1. **Валидация входных данных**:
   - Все переменные шаблона экранируются по умолчанию
   - Используйте StrictUndefined для отлова неопределенных переменных
   - Проверяйте входные данные перед рендерингом

2. **Контроль доступа**:
   - Храните чувствительные промпты отдельно
   - Используйте переменные окружения для чувствительных данных
   - При необходимости реализуйте контроль доступа к промптам

Для получения дополнительной информации о Jinja шаблонах в LLM приложениях, см. [документацию Instructor по интеграции с Jinja](https://python.useinstructor.com/blog/2024/09/19/instructor-proposal-integrating-jinja-templating/).