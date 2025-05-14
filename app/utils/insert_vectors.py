import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

import json  # noqa: E402
from datetime import datetime  # noqa: E402

import pandas as pd  # noqa: E402
from services.vector_store import VectorStore  # noqa: E402
from timescale_vector.client import uuid_from_time  # noqa: E402
from minio import Minio  # noqa: E402
from minio.error import S3Error  # noqa: E402

# Initialize VectorStore and MinIO client
vec = VectorStore(local=True)

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


# Prepare data for insertion
def prepare_record(row):
    """Prepare a record for insertion into the vector store.

    This function creates a record with a UUID version 1 as the ID, which captures
    the current time or a specified time.

    Note:
        - By default, this function uses the current time for the UUID.
        - To use a specific time:
          1. Import the datetime module.
          2. Create a datetime object for your desired time.
          3. Use uuid_from_time(your_datetime) instead of uuid_from_time(datetime.now()).

        Example:
            from datetime import datetime
            specific_time = datetime(2023, 1, 1, 12, 0, 0)
            id = str(uuid_from_time(specific_time))

        This is useful when your content already has an associated datetime.
    """
    content = f"Question: {row['question']}\nAnswer: {row['answer']}"
    embedding = vec.get_embedding(content)
    return pd.Series(
        {
            "id": str(uuid_from_time(datetime.now())),
            "metadata": {
                "category": row["category"],
                "created_at": datetime.now().isoformat(),
            },
            "contents": content,
            "embedding": embedding,
        }
    )


# Load data from JSON file
data = load_data()
df = pd.DataFrame(data)
records_df = df.apply(prepare_record, axis=1)

# Create tables and insert data
vec.create_tables()
try:
    vec.create_index()  # DiskAnnIndex
except Exception as e:
    if "already exists" in str(e):
        print("Index already exists, skipping creation")
    else:
        raise e
vec.upsert(records_df)
