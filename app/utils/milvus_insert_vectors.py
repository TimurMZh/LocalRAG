import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

from services.milvus_vector_store import MilvusVectorStore

import json
from datetime import datetime

import pandas as pd
from timescale_vector.client import uuid_from_time
from minio import Minio
from minio.error import S3Error


# Initialize VectorStore and MinIO client
vec = MilvusVectorStore()

minio_client = Minio(
    "localhost:9000",  # MinIO server address
    access_key="minioadmin",  # Default access key
    secret_key="minioadmin",  # Default secret key
    secure=False,  # Set to True if using HTTPS
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
        # First check if file exists in MinIO
        data_file = app_root.parent / "data" / "dataset.json"
        minio_path = "dataset.json"

        # Try to get the file from MinIO
        data = minio_client.get_object(BUCKET_NAME, minio_path)
        return json.loads(data.read().decode("utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, S3Error) as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)


def prepare_record(row):
    content = f"Question: {row['question']}\nAnswer: {row['answer']}"
    embedding = vec.get_embedding(content)
    return pd.Series(
        {
            "id": str(uuid_from_time(datetime.now())),
            "category": row["category"],
            "created_at": datetime.now().isoformat(),
            "contents": content,
            "embeddings": embedding,
        }
    )


# Load data from JSON file
data = load_data()

df = pd.DataFrame(data)
records_df = df.apply(prepare_record, axis=1)


if vec.is_connected:
    print("✅ Подключение к Milvus установлено!")
    # vec.create_tables()
    # vec.create_index()
    vec.insert(records_df)
    # vec.upsert(records_df)
else:
    print("❌ К сожалению подключение к Milvus не установлено!")



