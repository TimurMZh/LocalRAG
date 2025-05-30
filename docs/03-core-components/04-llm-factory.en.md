# LLM Factory and Structured Output

The LLM Factory in the Repository provides a unified interface for working with various LLM providers, ensuring structured output through the Instructor library. The factory pattern abstracts provider-specific implementations while guaranteeing consistent handling of structured input and output data.

## Architecture Overview

The system is built on three main components:

1. **LLM Provider Interface**: Abstract base class defining the contract for all providers
2. **Provider Implementations**: Concrete implementations for each supported LLM service
3. **Factory Class**: Creates and configures provider instances

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

## Instructor Integration

The LLM Factory uses [Instructor](https://python.useinstructor.com/) to ensure structured output from LLMs. Instructor modifies provider clients to:

- Ensure Pydantic model validation
- Handle retries on validation errors
- Provide consistent response structures
- Ensure type-safe interaction with LLMs

For more information about using Instructor with different providers, see the [Instructor documentation](https://python.useinstructor.com/providers/overview).

## Why Use Instructor Instead of Native Structured Output

While OpenAI now offers native structured output, Instructor continues to provide significant advantages that make it valuable for production applications:

1. **Cross-provider compatibility**: Instructor provides a unified API for different LLM providers (OpenAI, Anthropic, etc.), preventing vendor lock-in
2. **Advanced validation and retries**: Automatic validation and retry logic for failed response validation, with context preservation
3. **Streaming capabilities**: Simplified streaming with partial validation support
4. **Stable performance**: More consistent latency compared to native structured output

According to [recent tests](https://python.useinstructor.com/blog/2024/08/20/should-i-be-using-structured-outputs/), native structured output showed significant latency variation:

| Mode              | Average (s) | Max (s) | Std Dev |
|-------------------|-------------|-----------|--------------|
| Tool Calling      | 6.84        | 12.84     | 0.69         |
| Structured Outputs| 28.20       | 136.90    | 9.27         |

Using Instructor in the LLM Factory provides more reliable and stable performance while maintaining flexibility between providers.

## Provider Implementation

The LLM Factory supports three providers "out of the box":

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

Each provider is implemented using Instructor for structured output:

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

## Usage in LLM Nodes

Here's an example of using the LLM Factory in a node:

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

## Extending with New Providers

To add a new provider:

1. Create a new provider class:
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

2. Add to the provider map:
```python
providers = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "llama": LlamaProvider,
    "new_provider": NewProvider,  # Add your new provider
}
```

## Configuration

Provider settings are managed through the configuration system:

```python
# config/llm_config.py
class OpenAISettings(LLMProviderSettings):
    api_key: str = os.getenv("OPENAI_API_KEY")
    default_model: str = "gpt-4"
    max_tokens: int = 1000
    temperature: float = 0.0
```

This ensures consistent configuration across your application while allowing environment-specific overrides. 