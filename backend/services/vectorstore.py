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


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        collection_name = os.getenv("CHROMA_COLLECTION", "mortgage_docs")
        client = get_client()
        _collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
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
