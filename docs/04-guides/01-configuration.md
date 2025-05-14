# Управление конфигурацией

Система конфигурации в Репозитории использует Pydantic Settings для надежного управления конфигурацией с проверкой типов. Такой подход гарантирует, что все значения конфигурации проверяются при запуске, предотвращая ошибки времени выполнения из-за неправильной конфигурации.

## Архитектура конфигурации

Система конфигурации построена вокруг иерархической структуры, где settings.py служит центральным узлом конфигурации. Каждый основной компонент имеет свой собственный класс конфигурации, и все они объединяются в основной класс Settings.

```python
class Settings(BaseSettings):
    app_name: str = "GenAI Project Template"
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()
```
## Основные компоненты конфигурации

### Конфигурация базы данных (database_config.py)

Конфигурация базы данных управляет всеми настройками, связанными с базой данных, включая конфигурации векторного хранилища. Она предоставляет разумные значения по умолчанию, позволяя при этом переопределять их через переменные окружения:

```python
class DatabaseConfig(BaseSettings):
    host: str = os.getenv("DATABASE_HOST", "launchpad_database")
    port: str = os.getenv("DATABASE_PORT", "5432")
    name: str = os.getenv("DATABASE_NAME", "launchpad")
    
    @property
    def service_url(self) -> str:
        return f"postgres://{self.pg_user}:{self.password}@{self.host}:{self.port}/{self.name}"
```
### Конфигурация LLM (llm_config.py)

Конфигурация LLM управляет настройками для различных AI провайдеров. Она реализует паттерн конфигурации, специфичный для каждого провайдера:

```python
class LLMConfig(BaseSettings):
    openai: OpenAISettings = OpenAISettings()
    anthropic: AnthropicSettings = AnthropicSettings()
    llama: LlamaSettings = LlamaSettings()
```

Каждый провайдер имеет свой собственный класс настроек с конкретными конфигурациями:

```python
class OpenAISettings(LLMProviderSettings):
    api_key: str = os.getenv("OPENAI_API_KEY")
    default_model: str = "gpt-4"
    embedding_model: str = "text-embedding-3-small"
```

### Конфигурация Celery (celery_config.py)

Конфигурация Celery управляет настройками задач очереди, предоставляя чистый интерфейс для Celery:

```python
@lru_cache
def get_celery_config():
    redis_url = get_redis_url()
    return {
        "broker_url": redis_url,
        "result_backend": redis_url,
        "task_serializer": "json",
        "accept_content": ["json"]
    }
```

## Управление переменными окружения

Система конфигурации интегрируется с переменными окружения через Python-dotenv:

```python
from dotenv import load_dotenv
load_dotenv()
```

Это позволяет использовать разные конфигурационные файлы для каждой среды при необходимости:

- `.env` для локальной разработки
- `.env.staging` для среды тестирования
- `.env.production` для производственной среды

## Лучшие практики конфигурации

### Кэширование конфигурации

Мы используем Python's lru_cache для предотвращения повторного парсинга конфигурационных файлов:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```
### Типобезопасность

Все классы конфигурации наследуются от BaseSettings, обеспечивая валидацию типов:

```python
class VectorStoreConfig(BaseSettings):
    table_name: str = "embeddings"
    embedding_dimensions: int = 1536
    time_partition_interval: timedelta = timedelta(days=7)
```

### Вычисляемые свойства

Сложные конфигурационные значения могут быть вычислены с помощью properties:

```python
@property
def service_url(self) -> str:
    if self.local:
        return f"postgres://{self.pg_user}:{self.password}@localhost:{self.port}/{self.name}"
    return f"postgres://{self.pg_user}:{self.password}@{self.host}:{self.port}/{self.name}"
```
## Соображения безопасности

Система конфигурации реализует несколько лучших практик безопасности:

1. Чувствительные значения никогда не хардкодятся
2. API ключи загружаются из переменных окружения
3. Разные конфигурации для разных сред
4. Валидация критичных для безопасности настроек при запуске

## Расширение конфигурации

Чтобы добавить новые параметры конфигурации:

1. При необходимости создайте новый класс конфигурации
2. Добавьте новые настройки в соответствующий класс конфигурации
3. Обновите основной класс Settings, если добавляете новую категорию конфигурации

Пример добавления новой категории конфигурации:

```python
class CacheConfig(BaseSettings):
    ttl: int = 3600
    backend: str = "redis"
    prefix: str = "cache"

class Settings(BaseSettings):
    # Existing configs...
    cache: CacheConfig = CacheConfig()
```

## Использование конфигурации

В Репозитории доступ к конфигурации осуществляется через функцию get_settings:

```python
from config.settings import get_settings

settings = get_settings()
database_url = settings.database.service_url
openai_key = settings.llm.openai.api_key
```

Это обеспечивает согласованный доступ к конфигурационным значениям в приложении, сохраняя преимущества кэширования и валидации. 
