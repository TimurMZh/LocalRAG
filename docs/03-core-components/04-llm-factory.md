# LLM Factory и структурированный вывод

LLM Factory в Репозитории предоставляет унифицированный интерфейс для работы с различными LLM провайдерами, обеспечивая структурированный вывод с помощью библиотеки Instructor. Паттерн factory абстрагирует специфичные для провайдеров реализации, гарантируя при этом согласованную обработку структурированных входных и выходных данных.

## Обзор архитектуры

Система построена на трех основных компонентах:

1. **LLM Provider Interface**: Абстрактный базовый класс, определяющий контракт для всех провайдеров
2. **Provider Implementations**: Конкретные реализации для каждого поддерживаемого LLM сервиса
3. **Factory Class**: Создает и конфигурирует экземпляры провайдеров

```python
from services.llm_factory import LLMFactory
from pydantic import BaseModel, Field

# Initialize factory with specific provider
factory = LLMFactory("openai")

# Create completion with structured output
response_model, completion = factory.create_completion(
    response_model=YourResponseModel,
    messages=[
        {"role": "system", "content": "Your system prompt"},
        {"role": "user", "content": "Your user message"}
    ]
)
```
## Интеграция с Instructor

LLM Factory использует [Instructor](https://python.useinstructor.com/) для обеспечения структурированного вывода от LLM. Instructor модифицирует клиенты провайдеров для:

- Обеспечения валидации Pydantic моделей
- Обработки повторных попыток при ошибках валидации
- Предоставления согласованных структур ответов
- Обеспечения типобезопасного взаимодействия с LLM

Для получения дополнительной информации об использовании Instructor с различными провайдерами, см. [документацию Instructor](https://python.useinstructor.com/providers/overview).

## Почему использовать Instructor вместо нативного структурированного вывода

Хотя OpenAI теперь предлагает нативный структурированный вывод, Instructor продолжает предоставлять значительные преимущества, которые делают его ценным для production-приложений:

1. **Кросс-провайдерная совместимость**: Instructor предоставляет унифицированный API для различных LLM провайдеров (OpenAI, Anthropic и др.), предотвращая привязку к конкретному вендору
2. **Продвинутая валидация и повторные попытки**: Автоматическая валидация и логика повторных попыток при неудачной валидации ответов, с сохранением контекста
3. **Возможности стриминга**: Упрощенный стриминг с поддержкой частичной валидации
4. **Стабильная производительность**: Более стабильная задержка по сравнению с нативным структурированным выводом

Согласно [недавним тестам](https://python.useinstructor.com/blog/2024/08/20/should-i-be-using-structured-outputs/), нативный структурированный вывод показал значительную вариативность задержек:

| Режим              | Среднее (с) | Макс (с) | Станд. откл. |
|-------------------|-------------|-----------|--------------|
| Tool Calling      | 6.84        | 12.84     | 0.69         |
| Structured Outputs| 28.20       | 136.90    | 9.27         |

Использование Instructor в LLM Factory обеспечивает более надежную и стабильную производительность при сохранении гибкости между провайдерами.

## Реализация провайдеров

LLM Factory поддерживает три провайдера "из коробки":

```python
class LLMFactory:
    def _create_provider(self) -> LLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "llama": LlamaProvider,
        }
        provider_class = providers.get(self.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {self.provider}")
        return provider_class(self.settings)
```

Каждый провайдер реализован с использованием Instructor для структурированного вывода:

### OpenAI Provider
```python
class OpenAIProvider(LLMProvider):
    def _initialize_client(self) -> Any:
        return instructor.from_openai(
            OpenAI(api_key=self.settings.api_key)
        )
```

### Anthropic Provider
```python
class AnthropicProvider(LLMProvider):
    def _initialize_client(self) -> Any:
        return instructor.from_anthropic(
            Anthropic(api_key=self.settings.api_key)
        )
```

### Llama Provider
```python
class LlamaProvider(LLMProvider):
    def _initialize_client(self) -> Any:
        return instructor.from_openai(
            OpenAI(
                base_url=self.settings.base_url,
                api_key=self.settings.api_key
            ),
            mode=instructor.Mode.JSON
        )
```

## Использование в LLM узлах

Вот пример использования LLM Factory в узле:

```python
class AnalyzeTicket(LLMNode):
    class ContextModel(BaseModel):
        sender: str
        subject: str
        body: str

    class ResponseModel(BaseModel):
        reasoning: str = Field(
            description="Explain your reasoning for the intent classification"
        )
        intent: CustomerIntent
        confidence: float = Field(
            ge=0, le=1,
            description="Confidence score for the intent"
        )
        escalate: bool = Field(
            description="Flag for escalation needs"
        )

    def get_context(self, task_context: TaskContext) -> ContextModel:
        return self.ContextModel(
            sender=task_context.event.sender,
            subject=task_context.event.subject,
            body=task_context.event.body,
        )

    def create_completion(self, context: ContextModel) -> ResponseModel:
        llm = LLMFactory("openai")
        prompt = PromptManager.get_prompt(
            "ticket_analysis",
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
                    "content": f"# New ticket:\n{context.model_dump()}",
                },
            ],
        )
```

## Расширение с новыми провайдерами

Чтобы добавить новый провайдер:

1. Создайте новый класс провайдера:
```python
class NewProvider(LLMProvider):
    def _initialize_client(self) -> Any:
        return instructor.patch(
            YourClient(api_key=self.settings.api_key)
        )

    def create_completion(
        self,
        response_model: Type[BaseModel],
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Tuple[BaseModel, Any]:
        # Implement provider-specific completion logic
        pass
```

2. Добавьте в карту провайдеров:
```python
providers = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "llama": LlamaProvider,
    "new_provider": NewProvider,  # Add your new provider
}
```


## Конфигурация

Настройки провайдеров управляются через систему конфигурации:

```python
# config/llm_config.py
class OpenAISettings(LLMProviderSettings):
    api_key: str = os.getenv("OPENAI_API_KEY")
    default_model: str = "gpt-4"
    max_tokens: int = 1000
    temperature: float = 0.0
```

Это обеспечивает согласованную конфигурацию в вашем приложении, позволяя переопределять настройки для конкретного окружения.