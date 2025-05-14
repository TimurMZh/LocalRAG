import logging
from transformers import AutoTokenizer, AutoModel
import torch
from typing import Any, List, Optional, Tuple, Union
from pymilvus import connections, utility
from pymilvus import FieldSchema, DataType, CollectionSchema, Collection, Connections
from config.settings import get_settings
import pandas as pd
from services.llm_factory import LLMFactory
from openai import OpenAI
from utils.timer import timer

import logging
import time
from openai import OpenAI, RateLimitError
from typing import List, Union, Dict, Any, Type


class MilvusVectorStore:
    def __init__(self, embedding_model: str = None):
        """
        Initialize the VectorStore with settings, OpenAI client, and Milvus connection.
        Sets up the connection to Milvus database and initializes the collection if it exists.
        
        Args:
            embedding_model (str): The embedding model to use. Options: "roberta" or "openai"
            alias (str): The alias to use for the Milvus connection. Defaults to "launchpad"
        """
        self.settings = get_settings()
        self.roberta_settings = self.settings.llm.roberta
        self.vector_settings = self.settings.database.vector_store
        self.embedding_model = embedding_model or self.settings.llm.openai.embedding_model
        
        if embedding_model == "openai":
            self.embedding_dim = self.vector_settings.embedding_dimensions
        elif embedding_model == "roberta":
            self.embedding_dim = self.roberta_settings.max_tokens
        else:
            raise ValueError(f"Unknown embedding model dimension for {embedding_model!r}")
            
        
 
        # Обновляем размерность в настройках для создания коллекции
        self.vector_settings.embedding_dimensions = self.embedding_dim

        self.settings = get_settings()
        settings = get_settings().database
        connections.connect(
            alias=settings.name,
            host=settings.host,
            port=settings.port,
            db_name=settings.name)

        self.collection_name = f"{self.settings.database.name}_{embedding_model}"

        self._collection = None
        if utility.has_collection(self.collection_name, using=settings.name):
            self._collection = Collection(name=self.collection_name, using=settings.name)
            self._collection.load()
        else:
            self.create_tables()
            self.create_index()
            self._collection.load()


    def is_connected(self) -> bool:
        """
        Check if the connection to the Milvus database is established.

        Returns:
            bool: True if connected, False otherwise
        """
        return connections.has_connection(self.settings.name)

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text using the selected embedding model.

        Args:
            text (str): Text to generate embeddings for

        Returns:
            List[float]: Vector embedding representation of the input text
        """
        text = text.replace("\n", " ")
        
        if self.embedding_model == "roberta":
            llm = LLMFactory("roberta")
        else:  # openai
            llm = LLMFactory("openai")

        with timer("Embedding generation"):
            embeddings = llm.get_embedding(text)

        return embeddings

    def create_tables(self) -> None:
        """
        Create collection schema and initialize the collection in Milvus.
        Defines fields for id, category, created_at, contents and vector embeddings.
        """
        print(f"[DEBUG] → collection={self.collection_name}, embedding_model={self.embedding_model}, embedding_dim={self.embedding_dim}")
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=360, is_primary=True),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=250),
            FieldSchema(name="contents", dtype=DataType.VARCHAR, max_length=60535),
            FieldSchema(name=self.vector_settings.table_name, dtype=DataType.FLOAT_VECTOR,
                        dim=self.embedding_dim)
        ]

        schema = CollectionSchema(fields=fields, enable_dynamic_field=True)
        self._collection = Collection(
            name=self.collection_name,
            schema=schema,
            using=self.collection_name
        )

    def create_tables_from_dataframe(self, dataframe: pd.DataFrame, collection_name=None) -> None:
        """
        Create a collection directly from a pandas DataFrame.

        Args:
            dataframe (pd.DataFrame): DataFrame containing the data to initialize the collection
        """
        self._collection = Collection.construct_from_dataframe(
            name=self.collection_name if collection_name == None else collection_name,
            dataframe=dataframe,
            primary_field='id',
            using=self.settings.database.name
        )

    def create_index(self) -> None:
        """
        Create a vector index on the embedding field to optimize vector similarity search.
        Uses DISKANN index type with IP (Inner Product) metric for similarity calculation.
        """
        index_params = {
            "metric_type": "IP",
            "index_type": "DISKANN",
            "params": {
                "search_list": 100
            }
        }

        self._collection.create_index(
            field_name=self.vector_settings.table_name,
            index_params=index_params
        )

    def drop_index(self) -> None:
        """
        Remove the index from the collection.
        """
        self._collection.drop_index()

    def insert(self, df: pd.DataFrame) -> None:
        """
         Insert data from a DataFrame into the collection.

        Args:
            df (pd.DataFrame): DataFrame containing the data to insert
        """
        print(df)
        self._collection.insert(data=df)
        self._collection.flush()
        self.create_index()
        print("✅ Данные загружены и записаны в Milvus!")
        self._collection.load()
        print("✅ Коллекция загружена в память!")

    def upsert(self, df: pd.DataFrame) -> None:
        """
        Insert or update data from a DataFrame in the collection.
        If records with the same primary key exist, they will be updated.

        Args:
            df (pd.DataFrame): DataFrame containing the data to insert or update
        """
        self._collection.upsert(data=df)
        self._collection.flush()
        self.create_index()
        self._collection.load()

    def delete(
            self,
            ids: List[str] = None,
            metadata_filter: dict = None,
            delete_all: bool = False,
    ) -> None:
        """
        Delete data from the collection based on various criteria.

        Args:
            ids (List[str], optional): List of IDs to delete
            metadata_filter (dict, optional): Dictionary of field-value pairs to filter records to delete
            delete_all (bool, optional): If True, delete all records in the collection

        Raises:
            ValueError: If none of the deletion criteria are provided
        """
        if delete_all:
            expr = "id like '%%'"
            self._collection.delete(expr)
            logging.info("Все данные удалены из коллекции")
            return

        if ids:
            expr = f"id in {ids}"
            self._collection.delete(expr)
            logging.info(f"Удалено {len(ids)} записей")
            return

        if metadata_filter:
            conditions = []
            for key, value in metadata_filter.items():
                if isinstance(value, str):
                    conditions.append(f"{key} == '{value}'")
                else:
                    conditions.append(f"{key} == {value}")

            expr = " and ".join(conditions)
            results = self._collection.delete(expr)
            logging.info(f"Удалено {results.delete_count} записей по фильтру {expr}")
            return

        raise ValueError("Необходимо указать ids, metadata_filter или delete_all=True")

    def search(self, query: str, top_k: int = 5) -> pd.DataFrame:
        """
        Perform semantic vector search using the query text.
        First generates an embedding for the query, then searches for similar vectors in the collection.

        Args:
            query (str): Search query text
            top_k (int): Number of top results to return

        Returns:
            pd.DataFrame: DataFrame with search results including ID, category, contents and distance metrics
        """
        search_results = []
        query_embd = self.get_embedding(query)

        with timer("Vector search"):

            results = self._collection.search(
                data=[query_embd],
                anns_field=self.vector_settings.table_name,
                param={"metric_type": "IP", "params": {"search_list": 100}},
                limit=top_k,
                output_fields=["id", "category", "contents", "created_at"]
            )
        for result in results:
            for hit in result:
                search_results.append({
                    "id": hit.id,
                    "category": hit.entity.category if hasattr(hit.entity, 'category') else None,
                    "contents": hit.entity.contents if hasattr(hit.entity, 'contents') else None,
                    "created_at": hit.entity.created_at if hasattr(hit.entity, 'created_at') else None,
                    "distance": hit.distance
                })

        return pd.DataFrame(search_results)

    def query(self) -> pd.DataFrame:
        """
         Perform a structured query to retrieve records where category equals 'customer'.

        Returns:
            pd.DataFrame: DataFrame with query results including ID, category, and contents
        """
        with timer("Vector query"):
            results = self._collection.query(
                expr="category == 'customer'",  # вернёт все записи, у которых category == 'customer'.
                output_fields=["id", "category", "contents", "created_at"],
                limit=5,
            )
        return pd.DataFrame(results)