# Installation Guide

This guide provides a detailed and comprehensive description of the Repository's development environment setup process. It is designed for developers who want to gain a complete understanding of the installation process, including detailed explanations of each component, security considerations, and troubleshooting steps. If you're looking for a faster setup process, please refer to the Quick Start guide.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.12 or higher
- Docker and Docker Compose
- Git
- Code editor (VS Code or Cursor recommended)

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone -b boilerplate https://github.com/noteldar/llm-pipeline
cd llm-pipeline
```

### 2. Environment Setup

Create and configure environment files:

```bash
cp app/.env.example app/.env
cp docker/.env.example docker/.env
```

Required environment variables:

```bash
# app/.env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional

# docker/.env
CADDY_DOMAIN=your_domain.com  # For production
```

### 3. Docker Environment

Navigate to the docker directory and start the containers:

```bash
cd docker
./start.sh
```

This command will:

- Build all necessary Docker images
- Start services defined in docker-compose.yml
- Initialize the database
- Set up Redis queue

### 3. Start Milvus Standalone Docker

Milvus is used for storing vector embeddings. Ensure Milvus is running before loading documents or executing queries. Run the following command:

```bash
cd docker
./start.sh milvus-standalone-docker-compose.yml
```

This command will start Milvus in standalone mode.

### 4. Initialize Milvus Database

After installing and starting Milvus Standalone, you need to initialize the database. Run the following script:

```bash
python app/utils/init_mivus_collection.py
```

This script will create the necessary collections and indexes in Milvus.

### 5. Database Setup

Run database migrations:

```bash
cd ../app
./makemigration.sh  # Create new migrations
./migrate.sh        # Apply migrations
```

### 6. Local Development Environment

Set up Python virtual environment:

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

## Verifying Installation

1. Check service status:
```bash
docker ps
```

Expected running containers:
- launchpad_api
- launchpad_database
- launchpad_redis
- launchpad_caddy

## Common Installation Issues

### Database Connection Errors
- Ensure PostgreSQL container is running
- Check database credentials in .env file
- Verify port 5432 is not used by another application

### Docker Issues
- Run `docker compose down -v` to clean up
- Run `./logs` script inside docker directory to view timestamped logs
- Ensure ports 8000, 5432, and 6379 are available

### Python Environment Issues
- Check Python version: `python --version`
- Ensure pip is updated: `pip install --upgrade pip`
- Verify virtual environment activation

## Security Notes

- Never commit .env files
- Regularly rotate API keys
- Use strong database passwords
- Keep Docker and its dependencies updated 