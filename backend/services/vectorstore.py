import os
import chromadb
from chromadb.config import Settings

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
        os.makedirs(db_path, exist_ok=True)
        _client = chromadb.PersistentClient(path=db_path)
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        collection_name = os.getenv("CHROMA_COLLECTION", "health_docs")
        client = get_client()
        _collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_documents(
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> dict:
    collection = get_collection()
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return {"count": collection.count()}


def query_documents(
    query_text: str,
    n_results: int = 5,
    doc_ids: list[str] | None = None,
) -> dict:
    collection = get_collection()
    where_filter = None
    if doc_ids:
        where_filter = {"doc_id": {"$in": doc_ids}}

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    return results


def get_doc_count() -> int:
    collection = get_collection()
    return collection.count()
