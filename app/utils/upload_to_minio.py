from minio import Minio
from pathlib import Path

# Initialize MinIO client
minio_client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

# Define bucket name
BUCKET_NAME = "dataset-storage"

# Create bucket if it doesn't exist
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)

# Path to your dataset.json
data_file = Path("data/dataset.json")

# Upload file
with open(data_file, "rb") as f:
    minio_client.put_object(BUCKET_NAME, "dataset.json", f, length=data_file.stat().st_size)  # name in MinIO

print(f"Successfully uploaded {data_file} to MinIO bucket '{BUCKET_NAME}'")
