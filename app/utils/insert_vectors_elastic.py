import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
import asyncio  # noqa: E402

import pandas as pd  # noqa: E402
from services.vector_store import VectorStore  # noqa: E402
from database.elasticsearch_client import get_elasticsearch_client  # noqa: E402
from minio import Minio  # noqa: E402
from minio.error import S3Error  # noqa: E402

# Initialize VectorStore and Elasticsearch client
vec = VectorStore(local=True)
es_client = get_elasticsearch_client()

# Initialize MinIO client
minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

# Create bucket if it doesn't exist
BUCKET_NAME = "dataset-storage"
try:
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
except S3Error as e:
    print(f"Error initializing MinIO bucket: {e}")
    sys.exit(1)


def load_data():
    try:
        # Try to get the file from MinIO
        data = minio_client.get_object(BUCKET_NAME, "dataset.json")
        return json.loads(data.read().decode("utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, S3Error) as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)


def prepare_record(row):
    """Prepare a record for insertion into Elasticsearch"""
    content = f"Question: {row['question']}\nAnswer: {row['answer']}"
    embedding = vec.get_embedding(content)

    return {
        "content": content,
        "metadata": {
            "category": row["category"],
        },
        "embedding": embedding,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def main():
    try:
        # Delete existing index if it exists
        if await es_client.client.indices.exists(index=es_client.index_name):
            print(f"Deleting existing index: {es_client.index_name}")
            await es_client.client.indices.delete(index=es_client.index_name)
            print("Index deleted successfully")

        # Initialize Elasticsearch index with new mapping
        print("Creating new index with updated mapping...")
        await es_client.init()
        print("Index created successfully")

        # Load and prepare data
        data = load_data()
        df = pd.DataFrame(data)

        # Process and insert records
        for idx, row in df.iterrows():
            record = prepare_record(row)
            doc_id = str(idx)

            try:
                await es_client.index_document(doc_id=doc_id, document=record)
                if (idx + 1) % 100 == 0:
                    print(f"Processed {idx + 1} records")
            except Exception as e:
                print(f"Error inserting document {doc_id}: {e}")
    finally:
        # Ensure the client is properly closed
        await es_client.close()


if __name__ == "__main__":
    asyncio.run(main())
