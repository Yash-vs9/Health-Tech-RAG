import os
import chromadb
from chromadb.config import Settings
from backend.logging_config import get_logger

logger = get_logger("backend.vectorstore")

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
        os.makedirs(db_path, exist_ok=True)
        logger.info("Connecting to ChromaDB — path=%s", db_path)
        _client = chromadb.PersistentClient(path=db_path)
        logger.info("ChromaDB connected")
    return _client


def _get_expected_dim() -> int:
    """Get the embedding dimension for the current provider."""
    from backend.services.embeddings import get_embeddings
    embeddings = get_embeddings()
    # Embed a probe text to discover the dimension
    probe = embeddings.embed_query("dimension check")
    return len(probe)


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        collection_name = os.getenv("CHROMA_COLLECTION", "mortgage_docs")
        client = get_client()

        existing = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Validate embedding dimension matches stored collection
        if existing.count() > 0:
            try:
                peek = existing.peek(limit=1)
                stored_dim = len(peek["embeddings"][0])
                expected_dim = _get_expected_dim()
                if stored_dim != expected_dim:
                    logger.warning(
                        "Dimension mismatch — stored=%d, expected=%d. Resetting collection.",
                        stored_dim, expected_dim,
                    )
                    client.delete_collection(collection_name)
                    existing = client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
                    # Also clear BM25
                    try:
                        from . import retriever
                        retriever._bm25_index = None
                        retriever._bm25_docs = []
                    except Exception:
                        pass
                    logger.info("Collection recreated — new_dim=%d", expected_dim)
            except Exception as e:
                logger.debug("Dimension check skipped — %s", e)

        _collection = existing
        logger.info("Collection ready — name=%s, count=%d", collection_name, _collection.count())
    return _collection


def add_documents(
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> dict:
    collection = get_collection()
    logger.debug("Adding %d documents to ChromaDB", len(documents))
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    count = collection.count()
    logger.info("Documents added — new_total=%d", count)
    return {"count": count}


def query_documents(
    query_text: str,
    n_results: int = 5,
    doc_ids: list[str] | None = None,
) -> dict:
    collection = get_collection()
    where_filter = None
    if doc_ids:
        where_filter = {"doc_id": {"$in": doc_ids}}

    logger.debug(
        "ChromaDB query — n=%d, filter=%s, q=%s",
        n_results, where_filter, query_text[:50],
    )
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    hit_count = len(results["documents"][0]) if results["documents"] else 0
    min_dist = min(results["distances"][0]) if results["distances"] and results["distances"][0] else None
    max_dist = max(results["distances"][0]) if results["distances"] and results["distances"][0] else None
    logger.debug(
        "ChromaDB results — hits=%d, min_dist=%.4f, max_dist=%.4f",
        hit_count, min_dist or 0, max_dist or 0,
    )

    return results


def get_doc_count() -> int:
    collection = get_collection()
    return collection.count()


def delete_by_doc_id(doc_id: str) -> int:
    """Delete all chunks for a given doc_id. Returns number of chunks removed."""
    collection = get_collection()
    results = collection.get(where={"doc_id": doc_id})
    if not results["ids"]:
        logger.debug("No chunks found for doc_id=%s", doc_id)
        return 0
    collection.delete(ids=results["ids"])
    logger.info("Deleted %d chunks for doc_id=%s", len(results["ids"]), doc_id)
    return len(results["ids"])


def reset_collection() -> None:
    """Delete and recreate the collection. Used when switching embedding models."""
    global _collection, _client
    client = get_client()
    collection_name = os.getenv("CHROMA_COLLECTION", "mortgage_docs")
    try:
        client.delete_collection(collection_name)
        logger.info("Deleted old collection — name=%s", collection_name)
    except Exception:
        logger.debug("Collection %s did not exist", collection_name)
    # Clear all cached references
    _collection = None
    _client = None
    # Also reset BM25 index in retriever
    try:
        from . import retriever
        retriever._bm25_index = None
        retriever._bm25_docs = []
        logger.info("BM25 index cleared")
    except Exception:
        pass
    get_collection()
    logger.info("Recreated collection — name=%s", collection_name)
