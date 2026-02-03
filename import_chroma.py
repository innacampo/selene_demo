import json
import logging
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def import_to_local_db(
    json_file: str,
    db_path: str = "user_data/user_med_db",
    collection_name: str = "medical_docs",
    batch_size: int = 500,
):
    """
    Import ChromaDB export JSON into local database.

    Expected format:
    {
        "export_metadata": {...},
        "ids": ["id1", "id2", ...],
        "documents": ["text1", "text2", ...],
        "metadatas": [{...}, {...}, ...]
    }
    """
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    # Setup ChromaDB
    logger.info(f"Connecting to ChromaDB at {db_path}")
    client = chromadb.PersistentClient(path=db_path)

    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.get_or_create_collection(
        name=collection_name, embedding_function=embedding_model
    )

    logger.info(
        f"Collection '{collection_name}' has {collection.count()} existing documents"
    )

    # Load JSON
    logger.info(f"Loading {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate format
    if not isinstance(data, dict) or "ids" not in data or "documents" not in data:
        raise ValueError(
            "Invalid JSON format. Expected: {ids: [], documents: [], metadatas: []}"
        )

    ids = data["ids"]
    documents = data["documents"]
    metadatas = data.get("metadatas", [{} for _ in ids])

    total = len(ids)
    if total == 0:
        logger.warning("No documents to import")
        return collection

    # Log export metadata if present
    if "export_metadata" in data:
        meta = data["export_metadata"]
        logger.info(
            f"Export info: {meta.get('files_processed', '?')} files, "
            f"{meta.get('total_chunks', '?')} chunks, "
            f"created {meta.get('created_at', 'unknown')}"
        )

    logger.info(f"Importing {total} documents")

    # Batch import
    imported = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]

        # Clean metadata (ChromaDB only accepts str, int, float, bool)
        clean_metas = []
        for meta in batch_meta:
            clean = {}
            for k, v in meta.items():
                if v is None:
                    clean[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean[k] = v
                elif isinstance(v, list):
                    clean[k] = ", ".join(str(x) for x in v)
                else:
                    clean[k] = str(v)
            clean_metas.append(clean)

        try:
            collection.add(ids=batch_ids, documents=batch_docs, metadatas=clean_metas)
            imported += len(batch_ids)
            logger.info(f"Progress: {imported}/{total} ({100 * imported / total:.1f}%)")

        except Exception as e:
            logger.error(f"Batch failed: {e}")
            errors += len(batch_ids)

    print(f"\n{'=' * 50}")
    print("Import Complete!")
    print(f"   Imported: {imported}")
    print(f"   Errors: {errors}")
    print(f"   Collection total: {collection.count()} documents")
    print(f"{'=' * 50}\n")

    return collection


def query_test(
    query: str,
    db_path: str = "user_data/user_med_db",
    collection_name: str = "medical_docs",
    n_results: int = 3,
):
    """Test query against the collection."""
    client = chromadb.PersistentClient(path=db_path)
    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_collection(
        name=collection_name, embedding_function=embedding_model
    )

    results = collection.query(query_texts=[query], n_results=n_results)

    print(f"\n Query: '{query}'\n")
    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        print(f"--- Result {i + 1} (distance: {dist:.4f}) ---")
        print(f"Source: {meta.get('source', 'unknown')}")
        print(f"Text: {doc[:200]}...")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import ChromaDB export JSON")
    parser.add_argument("json_file", help="JSON file to import")
    parser.add_argument("--db-path", default="user_data/user_med_db")
    parser.add_argument("--collection", default="medical_docs")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--test-query", help="Run test query after import")

    args = parser.parse_args()

    collection = import_to_local_db(
        args.json_file,
        db_path=args.db_path,
        collection_name=args.collection,
        batch_size=args.batch_size,
    )

    if args.test_query:
        query_test(args.test_query, args.db_path, args.collection)
