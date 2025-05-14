import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

from services.milvus_vector_store import MilvusVectorStore


vec = MilvusVectorStore()

query = "Technodom қандай кәсіби даму"

if vec.is_connected:
    print("✅ Подключение к Milvus установлено!")
    result = vec.search(query=query)
    # result = vec.query()
    print(result)
else:
    print("❌ К сожалению подключение к Milvus не установлено!")



