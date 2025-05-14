# Quick Start

This guide provides the minimal steps needed to quickly get the Repository up and running. It's perfect for developers who want to test the platform or get started with minimal setup. For more detailed information about the installation process, security recommendations, and troubleshooting, please refer to the Installation Guide.

## Prerequisites

- Python 3.12 or higher
- Docker and Docker Compose
- Git
- Code editor (VS Code or Cursor recommended)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/noteldar/llm-pipeline
cd llm-pipeline
```

### 2. Create and Configure Environment Files

```bash
cp app/.env.example app/.env
cp docker/.env.example docker/.env
```

You can leave the `docker/.env` file as is for quick start. However, you need to add your OpenAI API key to the `app/.env` file. Open `app/.env` and find the `OPENAI_API_KEY` variable. Replace its value with your actual OpenAI API key:

```yaml
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Create and Start Docker Containers

```bash
cd ./docker
./start.sh
```

### 3.1. Ensure Roberta-Kaz-Large Model is Downloaded

If you're using the Roberta-Kaz-Large model, ensure it's downloaded to the `models/roberta-kaz-large` folder. If the model is missing, download it manually or set up automatic download in the code. For example:

```bash
python app/models/download_model.py
```

This script will automatically download the model to the correct location.

### 3.2. Start Milvus Standalone Docker

Milvus is used for storing vector embeddings. Ensure Milvus is running before loading documents or executing queries. Run the following command:

```bash
cd docker
./start.sh milvus-standalone-docker-compose.yml
```

This command will start Milvus in standalone mode.

### 4. Create Database Migrations

```bash
cd ../app
./makemigration.sh  # Create a new migration
./migrate.sh        # Apply migrations
```

When prompted for a migration message, you can enter a brief description, such as "Initial migration" or "Launch".

### 5. Start Logging

```bash
cd ../docker
./logs.sh
```

### 6. Create Virtual Environment and Install Dependencies

```bash
# Create a new virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS and Linux:
source venv/bin/activate

# Install the required packages
cd app
pip install -r requirements.txt
```

### 7. Populate Vector Store

To initialize the vector store with sample data, run:

```bash
python app/utils/insert_vectors.py
```

### 7.1. Initialize Milvus Database

After installing and starting Milvus Standalone, you need to initialize the database. Run the following script:

```bash
python app/utils/init_mivus_collection.py
```

This script will create the necessary collections and indexes in Milvus.

### 8. Send an Event

Run the following command to send a test event using the invoice.json file and the requests library:

```bash
python requests/send_event.py
```

You should receive a `202` status code and see the response in the terminal where you're running `./logs.sh`. Here you should see that the invoice service was called and that the task completed successfully.

This step creates the necessary tables, indexes, and adds initial vector data to the database.

### 9. Check the Database

Connect to the database using your preferred database tool. Default settings:

- Host: localhost
- Port: 5432
- Database: launchpad
- Username: postgres
- Password: super-secret-postgres-password

In the `events` table, you should see the processed event. It contains the original data (JSON) in the `data` column and the processed event (JSON) in the `task_context` column.

### 9. Start the Frontend

The frontend provides a user interface for interacting with the system. To start the frontend, follow these steps:

1. Navigate to the `frontend` directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the frontend in development mode:

```bash
npm run dev
```

4. Open your browser and navigate to the URL shown in the console (usually http://localhost:5173).

### Main Web Interface Pages

After starting the frontend, the following pages are available:

- **Document Upload:** [http://localhost:5173/upload](http://localhost:5173/upload)
  - Page for uploading documents (TXT, DOCX, PDF, JSON, XML) to the system.

- **Document Search:** [http://localhost:5173/search](http://localhost:5173/search)
  - Interface for semantic search through uploaded documents.

- **AI Chat:** [http://localhost:5173/chat](http://localhost:5173/chat)
  - Page for chatting with the language model based on uploaded data.

### 10. Experiment in Playground

The playground directory contains several Python scripts to help you experiment with various Repository components:

- Use `playground/llm_playground.py` to experiment with LLM factory and structured output.
- Use `playground/pipeline_playground.py` to run the pipeline with various example events.
- Use `playground/prompt_playground.py` to test and improve prompt templates.

It's recommended to run them using the **Python interactive window**, which you can learn more about [here](https://youtu.be/mpk4Q5feWaw?t=1346).

If you're using VS Code or Cursor, I also recommend adding the following settings to your `.code-workspace` file to simplify working with imports and refactoring:

```json
"settings": {
  "jupyter.notebookFileRoot": "${workspaceFolder}/app",
  "python.analysis.extraPaths": ["./app"],
  "python.testing.pytestArgs": [
   "app"
  ],
}
```

To experiment with LLM factory and structured output:

```bash
python playground/llm_playground.py
```

To run the pipeline with a sample event:

```bash
python playground/pipeline_playground.py
```

To test prompt templates:

```bash
python playground/prompt_playground.py
```

Feel free to modify these scripts and use the example events in the `requests/events/` directory to better understand how various components work.

## Configuration

Configuration is managed through environment variables and settings files. Key configuration files:

- `app/.env`: Application settings
- `docker/.env`: Docker and service configurations
- `app/config/settings.py`: Application and LLM model settings

Refer to the `.env.example` files to see available options.

## Development Process

Here's a high-level action plan for adapting the template to your unique project:

1. Update '.env' files with your API keys and passwords
2. Update settings in `app/config`
3. Define events in `requests/events` (your incoming data)
4. Update API schema in `app/api/event_schema.py` (to match your events)
5. Define your AI pipelines and processing steps in `app/pipelines/`
6. Add your vector embeddings to the database using `app/utils/insert_vectors.py` (optional, for RAG)
7. Experiment with different AI models, data, and settings in 'playground'
8. Configure your pipelines and application flow

## Deployment

The project includes a complete Docker-based deployment strategy. To deploy:

1. Ensure your production configurations are set in the `.env` files.
2. Build and run Docker containers:

```bash
cd docker
./start.sh
```

Caddy is pre-configured to handle HTTPS, simplifying the deployment process.

## Troubleshooting

### Initial Deployment Errors

If you encounter errors during initial deployment, especially related to the database or missing tables, it's recommended to remove all containers and volumes to start fresh. This ensures you're working in a new environment without data conflicts from previous attempts.

Follow these steps to clean up your Docker environment:

1. Stop all running containers:

```bash
docker compose down
```

2. Remove all project-related containers:

```bash
docker rm $(docker ps -a -q --filter name=launchpad_*)
```

3. Remove all project-related volumes:

```bash
docker volume rm $(docker volume ls -q --filter name=launchpad_*)
```

4. Optionally, you can remove all unused volumes (be careful if you have other projects using Docker):

```bash
docker volume prune
```

5. Rebuild and start containers:

```bash
cd docker
./start.sh
```

6. Restart migration scripts:
 
```bash
cd ../app
./makemigration.sh
./migrate.sh
```

After completing these steps, you should have a clean environment to work with. If you continue to experience issues, please check the logs for more detailed error messages:

```bash
cd docker
./logs.sh
```

If problems persist, ensure all environment variables are set correctly in your `.env` files and that there are no conflicts with other services running on your machine. 