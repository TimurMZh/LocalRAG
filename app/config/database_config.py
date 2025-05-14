import os
from datetime import timedelta

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

"""
Configuration for the VectorStore.
"""


class VectorStoreConfig(BaseSettings):
    """Settings for the VectorStore."""

    provider: str = "milvus"
    table_name: str = "embeddings"
    embedding_dimensions: int = 1536
    time_partition_interval: timedelta = timedelta(days=7)


class DatabaseConfig(BaseSettings):
    """Settings for the database."""

    host: str = os.getenv("DATABASE_HOST", "launchpad_database")
    port: str = os.getenv("DATABASE_PORT", "5432")
    name: str = os.getenv("DATABASE_NAME", "launchpad")
    pg_user: str = os.getenv("DATABASE_USER", "postgres")
    password: str = os.getenv("DATABASE_PASSWORD")
    local: bool = False

    @property
    def service_url(self) -> str:
        """Generate the service URL based on the environment."""
        if self.local:
            return f"postgres://{self.pg_user}:{self.password}@localhost:{self.port}/{self.name}"
        return f"postgres://{self.pg_user}:{self.password}@{self.host}:{self.port}/{self.name}"

    vector_store: VectorStoreConfig = VectorStoreConfig()


def is_running_in_docker() -> bool:
    """
        Проверяет, запущен ли код внутри Docker-контейнера.
        Docker создаёт файл /.dockerenv в корне, если это контейнер.
    """
    return os.path.exists("/.dockerenv")


class MilvusDatabaseConfig(BaseSettings):
    # Адрес хоста Milvus — определяется автоматически:
    # - standalone (если внутри Docker)
    # - localhost (если запускается локально)
    host: str = "standalone" if is_running_in_docker() else "localhost"
    port: str = os.getenv("MILVUS_PORT", "19530")
    name: str = os.getenv("MILVUS_NAME", "launchpad")

    vector_store: VectorStoreConfig = VectorStoreConfig()

