"""
ChromaDB Knowledge Base Update and Synchronization Utility.

This script provides tools for:
- Importing section-aware JSON exports into a local ChromaDB instance.
- Non-destructive updates: Clearing document data while preserving collection references.
- Query testing with formatted citation outputs.
- Database statistics and inspection.
"""

import json
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from selene import settings

logger = logging.getLogger(__name__)


def import_to_local_db(
    json_file: str,
    db_path: str = settings.DB_PATH,
    collection_name: str = settings.MEDICAL_DOCS_COLLECTION,
    batch_size: int = 500,
) -> chromadb.Collection:
    """
    Import a JSON export of medical chunks into the local vector database.

    This function implements a 'safe clear' strategy: instead of deleting the
    collection object (which changes its internal ID and crashes running apps),
    it deletes all IDs inside the collection and repopulates them.

    Args:
        json_file: Path to the .json export file.
        db_path: Path to the ChromaDB persistent storage.
        collection_name: Name of the collection to target.
        batch_size: Number of documents to commit per transaction to avoid memory issues.

    Returns:
        chomadb.Collection: The updated collection object.
    """
    logger.debug(
        f"import_to_local_db: ENTER json_file={json_file}, db_path={db_path}, collection={collection_name}, batch_size={batch_size}"
    )
    json_path = Path(json_file)
    if not json_path.exists():
        logger.error(f"import_to_local_db: JSON file not found: {json_file}")
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    # Setup ChromaDB
    logger.info(f"Connecting to ChromaDB at {db_path}")
    logger.debug("import_to_local_db: Creating PersistentClient")
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=settings.CHROMA_TELEMETRY),
    )

    embedding_model = settings.get_embedding_function()

    collection = client.get_or_create_collection(
        name=collection_name, embedding_function=embedding_model
    )

    # Clear existing documents if collection was already present
    # This is non-destructive to the collection ID, preventing Stale Reference errors
    existing_count = collection.count()
    if existing_count > 0:
        logger.info(f"Clearing {existing_count} existing documents from '{collection_name}'...")
        # Get all IDs and delete them in batches if necessary
        # For simplicity, we get all IDs. If the DB is massive (>100k), this might need chunking.
        results = collection.get()
        if results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info("Collection cleared.")

    logger.info(f"Collection '{collection_name}' has {collection.count()} existing documents")

    # Load JSON
    logger.info(f"Loading {json_file}")
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    # Validate format
    if not isinstance(data, dict) or "ids" not in data or "documents" not in data:
        raise ValueError("Invalid JSON format. Expected: {ids: [], documents: [], metadatas: []}")

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

        logger.debug(
            f"import_to_local_db: Preparing batch {i // batch_size + 1} ({len(batch_ids)} docs)"
        )

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

        except Exception:
            logger.exception(
                "import_to_local_db: Batch failed - exception adding batch to collection"
            )
            errors += len(batch_ids)

    logger.debug(f"import_to_local_db: Import loop complete - imported={imported}, errors={errors}")

    logger.info("Import Complete")
    logger.info(f"   Imported: {imported}")
    logger.info(f"   Errors: {errors}")
    final_count = collection.count()
    logger.info(f"   Collection total after import: {final_count} documents")
    logger.debug("import_to_local_db: Exiting, returning collection")

    # Also print for CLI friendliness
    print(f"\n{'=' * 50}")
    print("Import Complete!")
    print(f"   Imported: {imported}")
    print(f"   Errors: {errors}")
    print(f"   Collection total: {final_count} documents")
    print(f"{'=' * 50}\n")

    # Invalidate RAG cache so queries use the new documents
    try:
        from selene.core.med_logic import invalidate_rag_cache

        invalidate_rag_cache()
        logger.info("RAG cache invalidated after knowledge base update")
    except ImportError:
        logger.warning("Could not import med_logic to invalidate cache")

    return collection


def query_with_sources(
    query: str,
    db_path: str = settings.DB_PATH,
    collection_name: str = settings.MEDICAL_DOCS_COLLECTION,
    n_results: int = 5,
) -> tuple[list[str], list[str], list[dict], list[float]]:
    """
    Search the vector database and extract unique source names.

    Args:
        query: The raw text string to embed and search.
        db_path: Path to ChromaDB.
        collection_name: Target collection.
        n_results: Max chunks to retrieve.

    Returns:
        Tuple: (List of chunk texts, List of unique source citations, List of full metadatas, List of distances)
    """
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=settings.CHROMA_TELEMETRY),
    )
    embedding_model = settings.get_embedding_function()
    collection = client.get_collection(name=collection_name, embedding_function=embedding_model)

    logger.debug(f"query_with_sources: ENTER query='{query[:80]}...', n_results={n_results}")
    results = collection.query(query_texts=[query], n_results=n_results)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    logger.debug(f"query_with_sources: Retrieved {len(documents)} chunks")

    # Extract unique sources
    sources = []
    seen_sources = set()

    for meta in metadatas:
        source = meta.get("source", "Unknown source")
        if source not in seen_sources:
            sources.append(source)
            seen_sources.add(source)

    logger.debug(f"query_with_sources: Unique sources found: {sources}")

    return documents, sources, metadatas, distances


def format_response_with_citations(query: str, llm_response: str, sources: list[str]) -> str:
    """
    Format LLM response with citations appended.

    Args:
        query: Original query
        llm_response: LLM's answer
        sources: List of source citations

    Returns:
        Formatted response with citations
    """
    logger.debug(
        f"format_response_with_citations: ENTER query='{query[:80]}...', llm_response_len={len(llm_response)}, sources_count={len(sources)}"
    )
    formatted = f"{llm_response}\n\n"

    if sources:
        formatted += "**Sources:**\n"
        for i, source in enumerate(sources, 1):
            formatted += f"{i}. {source}\n"

    logger.debug(f"format_response_with_citations: EXIT formatted_len={len(formatted)}")
    return formatted


def query_test(
    query: str,
    db_path: str = "user_data/user_med_db",
    collection_name: str = "medical_docs",
    n_results: int = 5,
) -> None:
    """
    Utility to run a test query and print a detailed breakdown of retrieved chunks.
    Useful for verifying RAG performance and source attribution.
    """
    logger.debug(f"query_test: ENTER query='{query}', n_results={n_results}")
    print(f"\n{'=' * 60}")
    print(f"Query: '{query}'")
    print(f"{'=' * 60}\n")

    documents, sources, metadatas, distances = query_with_sources(
        query, db_path, collection_name, n_results
    )
    logger.debug(
        f"query_test: Retrieved {len(documents)} documents and {len(sources)} unique sources"
    )

    print("RETRIEVED CONTEXT:")
    print("-" * 60)
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances, strict=False)):
        print(f"\n[{i + 1}] Relevance: {1 - dist:.3f}")
        print(f"Source: {meta.get('source', 'Unknown')}")
        if meta.get("chunk_index") is not None:
            print(f"Chunk: {meta['chunk_index'] + 1}/{meta.get('total_chunks', '?')}")
        print(f"Text: {doc[:300]}...")
        print()

    print("\n" + "=" * 60)
    print("UNIQUE SOURCES:")
    print("=" * 60)
    for i, source in enumerate(sources, 1):
        print(f"{i}. {source}")


def get_collection_stats(
    db_path: str = settings.DB_PATH,
    collection_name: str = settings.MEDICAL_DOCS_COLLECTION,
) -> None:
    """
    Print summary statistics about the collection, including total chunks
    and a sorted list of all unique ingested source files.
    """
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=settings.CHROMA_TELEMETRY),
    )
    embedding_model = settings.get_embedding_function()

    try:
        collection = client.get_collection(name=collection_name, embedding_function=embedding_model)
    except ValueError:
        print(f"Collection '{collection_name}' not found")
        return

    # Get all data
    all_data = collection.get()
    metadatas = all_data["metadatas"]

    # Count unique sources
    unique_sources = set()
    for meta in metadatas:
        if "source" in meta:
            unique_sources.add(meta["source"])

    logger.info("get_collection_stats: Retrieved collection statistics")
    logger.info(f"  Total chunks: {collection.count()}")
    logger.info(f"  Unique sources: {len(unique_sources)}")
    logger.debug(f"get_collection_stats: Sources sample: {sorted(unique_sources)[:10]}")

    print(f"\n{'=' * 60}")
    print("COLLECTION STATISTICS")
    print(f"{'=' * 60}")
    print(f"Total chunks: {collection.count()}")
    print(f"Unique sources: {len(unique_sources)}")
    print(f"\n{'=' * 60}")
    print("SOURCES IN DATABASE:")
    print(f"{'=' * 60}")
    for i, source in enumerate(sorted(unique_sources), 1):
        print(f"{i}. {source}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import ChromaDB export JSON with citation support"
    )
    parser.add_argument("json_file", nargs="?", help="JSON file to import")
    parser.add_argument("--db-path", default=settings.DB_PATH)
    parser.add_argument("--collection", default=settings.MEDICAL_DOCS_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--test-query", help="Run test query after import")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--query", help="Query the database without import")

    args = parser.parse_args()

    if args.stats:
        get_collection_stats(args.db_path, args.collection)
    elif args.query:
        query_test(args.query, args.db_path, args.collection)
    elif args.json_file:
        collection = import_to_local_db(
            args.json_file,
            db_path=args.db_path,
            collection_name=args.collection,
            batch_size=args.batch_size,
        )

        if args.test_query:
            query_test(args.test_query, args.db_path, args.collection)
    else:
        parser.print_help()
