# Руководство по установке

Это руководство предоставляет подробное и всестороннее описание процесса настройки среды разработки Репозитория. Оно предназначено для разработчиков, которые хотят получить полное понимание процесса установки, включая детальные объяснения каждого компонента, соображения безопасности и шаги по устранению неполадок. Если вы ищете более быстрый процесс настройки, обратитесь к руководству Быстрый старт.

## Предварительные требования

Прежде чем начать, убедитесь, что у вас установлено следующее:

- Python 3.12 или выше
- Docker и Docker Compose
- Git
- Редактор кода (рекомендуется VS Code или Cursor)

## Пошаговая установка

### 1. Клонирование репозитория

```bash
git clone -b boilerplate https://github.com/noteldar/llm-pipeline
cd llm-pipeline
```

### 2. Настройка окружения

Создайте и настройте файлы окружения:

```bash
cp app/.env.example app/.env
cp docker/.env.example docker/.env
```

Необходимые переменные окружения:

```bash
# app/.env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional

# docker/.env
CADDY_DOMAIN=your_domain.com  # For production
```

### 3. Docker Environment

Перейдите в директорию docker и запустите контейнеры:

```bash
cd docker
./start.sh
```

Эта команда:

- Соберет все необходимые Docker образы
- Запустит сервисы, определенные в docker-compose.yml
- Инициализирует базу данных
- Настроит Redis очередь

### 3. Запуск Milvus Standalone Docker

Milvus используется для хранения векторных эмбеддингов. Убедитесь, что Milvus запущен перед загрузкой документов или выполнением запросов. Для этого выполните следующую команду:

```bash
cd docker
./start.sh milvus-standalone-docker-compose.yml
```

Эта команда запустит Milvus в режиме standalone.

### 4. Инициализация базы данных Milvus

После установки и запуска Milvus Standalone, необходимо инициализировать базу данных. Для этого выполните следующий скрипт:

```bash
python app/utils/init_mivus_collection.py
```

Этот скрипт создаст необходимые коллекции и индексы в Milvus.

### 5. Настройка базы данных

Запустите миграции базы данных:

```bash
cd ../app
./makemigration.sh  # Create new migrations
./migrate.sh        # Apply migrations
```

### 6. Локальная среда разработки

Настройка виртуальной Python-окружения:

```bash
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# Install dependencies
cd app
pip install -r requirements.txt
```

## Проверка установки

1. Проверка статуса сервисов:
```bash
docker ps
```

Ожидаемые запущенные контейнеры:
- launchpad_api
- launchpad_database
- launchpad_redis
- launchpad_caddy

## Часто встречающиеся проблемы при установке

### Ошибки подключения к базе данных
- Убедитесь, что контейнер PostgreSQL запущен
- Проверьте учетные данные базы данных в файле .env
- Убедитесь, что порт 5432 не используется другим приложением

### Проблемы с Docker
- Запустите `docker compose down -v` для очистки
- Запустите скрипт `./logs` внутри директории docker для просмотра логов с временными метками
- Убедитесь, что порты 8000, 5432 и 6379 свободны

### Проблемы с Python окружением
- Проверьте версию Python: `python --version`
- Убедитесь, что pip обновлен: `pip install --upgrade pip`
- Проверьте активацию виртуального окружения

## Замечания по безопасности

- Никогда не коммитить файлы .env
- Периодически менять API ключи
- Использовать сильные пароли для базы данных
- Обновлять Docker и его зависимости