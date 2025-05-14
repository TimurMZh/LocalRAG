import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "app"))


from services.milvus_vector_store import MilvusVectorStore
from services.vector_store import VectorStore  # noqa: E402
from database import HybridSearchRepository, SessionLocal  # noqa: E402
from services.llm_factory import LLMFactory  # noqa: E402

"""
This playground demonstrates different search approaches including:
1. Pure semantic (vector) search
2. Pure keyword search
3. Hybrid search combining both approaches
"""


async def demonstrate_search_approaches():
    # vec = VectorStore()
    milvus_vec = MilvusVectorStore()
    llm = LLMFactory("roberta")
    session = SessionLocal()
    hybrid_repo = HybridSearchRepository(session)

    # Initialize Elasticsearch index
    print("\nInitializing Elasticsearch...")
    try:
        await hybrid_repo.es_client.init()
        print("Successfully initialized Elasticsearch index!")
    except Exception as e:
        print(f"Error initializing Elasticsearch index: {str(e)}")
        return

    # Add debug logging for Elasticsearch connection
    print("\nTesting Elasticsearch connection...")
    try:
        await hybrid_repo.es_client.client.info()
        print("Successfully connected to Elasticsearch!")
    except Exception as e:
        print(f"Elasticsearch connection error: {str(e)}")
        print(
            "Connection details:",
            {
                "host": hybrid_repo.es_client.client.transport.hosts,
                "ssl": hybrid_repo.es_client.client.transport.ssl_assert_fingerprint,
            },
        )
        return

    try:
        # Test query
        query = "Үйден жұмыс істеу саясаты қандай?"
        print("\n=== Testing different search approaches ===\n")

        # --------------------------------------------------------------
        # 1. Pure semantic search using vectors
        # --------------------------------------------------------------
        print("1. Semantic Search Results:")
        semantic_results = milvus_vec.search(query)
        print(f"Found {len(semantic_results)} results")
        for i, result in enumerate(semantic_results.itertuples(), 1):
            print(f"\n{i}. Distance: {result.distance:.3f}")
            print(f"Content: {result.contents[:200]}...")

        # --------------------------------------------------------------
        # 2. Pure keyword search
        # --------------------------------------------------------------
        # print("\n2. Keyword Search Results:")
        # keyword_results = vec.keyword_search("саясаты")
        # print(f"Found {len(keyword_results)} results")
        # for i, result in enumerate(keyword_results.itertuples(), 1):
        #     print(f"\n{i}. Rank: {result.rank:.3f}")
        #     print(f"Content: {result.contents[:200]}...")

        # --------------------------------------------------------------
        # 3. Hybrid search (combining semantic and keyword)
        # --------------------------------------------------------------
        print("\n3. Hybrid Search Results:")
        query_embedding = llm.get_embedding(query)

        try:
            hybrid_results = await hybrid_repo.hybrid_search(
                query=query,
                query_vector=query_embedding,
                weight_text=0.3,
                weight_vector=0.7,
                size=3,
                return_raw_es=True,
            )

            print(f"Found {len(hybrid_results)} results")
            for i, result in enumerate(hybrid_results, 1):
                result_id = result.get("_id") if isinstance(result, dict) else result.id
                content = (
                    result.get("_source", {}).get("content", "")
                    if isinstance(result, dict)
                    else result.data.get("content", "")
                )

                print(f"\n{i}. Event ID: {result_id}")
                print(f"Content: {content[:200]}...")

        except Exception as e:
            print(f"Error in hybrid search: {str(e)}")
            print("Full error details:", e.__class__.__name__)
            import traceback

            traceback.print_exc()

        # --------------------------------------------------------------
        # 4. Compare results
        # --------------------------------------------------------------
        print("\n=== Search Approach Comparison ===")
        print("\nSemantic Search: Best for understanding context and meaning")
        print("Keyword Search: Best for exact matches and specific terms")
        print("Hybrid Search: Balanced approach combining both methods")

        # --------------------------------------------------------------
        # 5. Experiment with different weights
        # --------------------------------------------------------------
        print("\n=== Testing Different Hybrid Weights ===")
        weight_combinations = [
            (0.8, 0.2),  # Favor text matching
            (0.2, 0.8),  # Favor semantic similarity
            (0.5, 0.5),  # Equal weights
        ]

        for text_weight, vector_weight in weight_combinations:
            print(f"\nWeights - Text: {text_weight:.1f}, Vector: {vector_weight:.1f}")
            results = await hybrid_repo.hybrid_search(
                query=query,
                query_vector=query_embedding,
                weight_text=text_weight,
                weight_vector=vector_weight,
                size=3,
                return_raw_es=True,
            )
            for i, result in enumerate(results, 1):
                result_id = result.get("_id") if isinstance(result, dict) else result.id
                content = (
                    result.get("_source", {}).get("content", "")
                    if isinstance(result, dict)
                    else result.data.get("content", "")
                )
                print(f"\n{i}. Event ID: {result_id}")
                print(f"Content: {content[:200]}...")

    finally:
        # Properly close all connections
        session.close()
        await hybrid_repo.es_client.client.close()  # Close ES client
        # If vec or llm have any cleanup needed, add it here


if __name__ == "__main__":
    # Run the async demonstration
    asyncio.run(demonstrate_search_approaches())
