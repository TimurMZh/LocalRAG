"""
Скрипт для инициализации коллекций Milvus для разных моделей эмбеддингов.
Создает отдельные коллекции для RoBERTa и OpenAI, а также создает индексы для оптимизации поиска.
"""

import argparse
from typing import List, Optional
import sys
from pathlib import Path
import time

app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

from pymilvus import connections, utility
from pymilvus import FieldSchema, DataType, CollectionSchema, Collection

from config.settings import get_settings
from services.milvus_vector_store import MilvusVectorStore

def connect_to_milvus(settings) -> bool:
    """
    Подключается к Milvus.
    
    Args:
        settings: Настройки приложения
        
    Returns:
        bool: True, если подключение установлено успешно, иначе False
    """
    try:
        # Подключаемся к Milvus с указанием базы данных
        connections.connect(
            alias=settings.database.name,
            host=settings.database.host,
            port=settings.database.port,
            db_name=settings.database.name
        )
        return True
    except Exception as e:
        print(f"Ошибка подключения к Milvus: {e}")
        return False


def list_collections(settings) -> List[str]:
    """
    Получает список всех коллекций в Milvus.
    
    Args:
        settings: Настройки приложения
        
    Returns:
        List[str]: Список имен коллекций
    """
    try:
        collections = utility.list_collections(using=settings.database.name)
        return collections
    except Exception as e:
        print(f"Ошибка получения списка коллекций: {e}")
        return []


def create_collection(settings, embedding_model: str) -> Optional[Collection]:
    """
    Создает коллекцию для указанной модели эмбеддингов.
    
    Args:
        settings: Настройки приложения
        embedding_model: Модель эмбеддингов ("roberta" или "openai")
        
    Returns:
        Optional[Collection]: Созданная коллекция или None в случае ошибки
    """
    try:
        # Определяем размерность эмбеддингов
        if embedding_model == "openai":
            embedding_dim = settings.database.vector_store.embedding_dimensions
        elif embedding_model == "roberta":
            embedding_dim = settings.llm.roberta.max_tokens
        else:
            raise ValueError(f"Неизвестная модель эмбеддингов: {embedding_model}")
        
        # Создаем имя коллекции
        collection_name = f"{settings.database.name}_{embedding_model}"
        
        # Создаем схему коллекции
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=360, is_primary=True),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=250),
            FieldSchema(name="contents", dtype=DataType.VARCHAR, max_length=60535),
            FieldSchema(name=settings.database.vector_store.table_name, dtype=DataType.FLOAT_VECTOR,
                        dim=embedding_dim)
        ]
        
        schema = CollectionSchema(fields=fields, enable_dynamic_field=True)
        
        # Создаем коллекцию
        collection = Collection(
            name=collection_name,
            schema=schema,
            using=settings.database.name
        )
        
        print(f"Создана коллекция: {collection_name}")
        
        # Создаем индекс
        index_params = {
            "metric_type": "IP",
            "index_type": "DISKANN",
            "params": {
                "search_list": 100
            }
        }
        
        collection.create_index(
            field_name=settings.database.vector_store.table_name,
            index_params=index_params
        )
        
        print(f"Создан индекс для коллекции: {collection_name}")
        
        return collection
    except Exception as e:
        print(f"Ошибка создания коллекции для {embedding_model}: {e}")
        return None


def drop_collection(settings, collection_name: str) -> bool:
    """
    Удаляет коллекцию из Milvus.
    
    Args:
        settings: Настройки приложения
        collection_name: Имя коллекции для удаления
        
    Returns:
        bool: True, если коллекция успешно удалена, иначе False
    """
    try:
        utility.drop_collection(collection_name, using=settings.database.name)
        print(f"Коллекция удалена: {collection_name}")
        return True
    except Exception as e:
        print(f"Ошибка удаления коллекции {collection_name}: {e}")
        return False


def init_collections(settings, force: bool = False) -> None:
    """
    Инициализирует коллекции для всех поддерживаемых моделей эмбеддингов.
    
    Args:
        settings: Настройки приложения
        force: Если True, пересоздает коллекции, даже если они уже существуют
    """
    # Поддерживаемые модели эмбеддингов
    embedding_models = ["roberta", "openai"]
    
    # Получаем список существующих коллекций
    existing_collections = list_collections(settings)
    
    for model in embedding_models:
        collection_name = f"{settings.database.name}_{model}"
        
        # Если коллекция уже существует и force=False, пропускаем
        if collection_name in existing_collections and not force:
            print(f"Коллекция {collection_name} уже существует, пропускаем")
            continue
        
        # Если коллекция существует и force=True, удаляем ее
        if collection_name in existing_collections and force:
            print(f"Пересоздание коллекции {collection_name}")
            drop_collection(settings, collection_name)
        
        # Создаем новую коллекцию
        create_collection(settings, model)


def main():
    """
    Основная функция скрипта.
    """
    parser = argparse.ArgumentParser(description="Инициализация коллекций Milvus")
    parser.add_argument("--force", action="store_true", help="Пересоздать коллекции, даже если они уже существуют")
    args = parser.parse_args()
    
    # Получаем настройки приложения
    settings = get_settings()
    
    # Подключаемся к Milvus
    if not connect_to_milvus(settings):
        return
    
    # Инициализируем коллекции
    init_collections(settings, force=args.force)
    
    print("Инициализация коллекций Milvus успешно завершена")


if __name__ == "__main__":
    main()
