"""
Qdrant vector store — collection management, upsert, query, delete.

All vector operations go through this module. The collection is auto-created
on first use with 4096-dim COSINE distance. A payload index on "doc_id"
enables efficient filtering by document.

Functions:
    get_client() -> QdrantClient
    get_collection() -> str               - Ensure collection exists, return name
    add_documents(docs, metas, ids) -> dict - Batch embed + upsert (with retry)
    query_documents(query, n_results, doc_ids) -> dict - Semantic search
    get_doc_count() -> int
    delete_by_doc_id(doc_id) -> int       - Delete all chunks for a doc
    reset_collection() -> None            - Delete + recreate collection

Env vars used:
    QDRANT_URL         - Server URL (default: http://localhost:6333)
    QDRANT_API_KEY     - For Qdrant Cloud
    QDRANT_COLLECTION  - Collection name (default: "mortgage_docs")
    QDRANT_TIMEOUT     - Request timeout (default: 120s)
    QDRANT_BATCH_SIZE  - Upsert batch size (default: 50)

Chunk ID format: UUID v5 derived from "{doc_id}::chunk_{index}"
"""

import os
import time
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
)
from backend.logging_config import get_logger

logger = get_logger("backend.vectorstore")

EMBEDDING_DIM = 4096
_UUID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

_client: QdrantClient | None = None
_collection_name: str | None = None
_version: int = 0


def _to_uuid(value: str) -> str:
    """Convert any string to a deterministic, valid UUID v5."""
    return str(uuid.uuid5(_UUID_NAMESPACE, value))


def _get_collection_name() -> str:
    global _collection_name
    if _collection_name is None:
        _collection_name = os.getenv("QDRANT_COLLECTION", "mortgage_docs")
    return _collection_name


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY", None) or None
        timeout = int(os.getenv("QDRANT_TIMEOUT", "120"))
        logger.info("Connecting to Qdrant — url=%s, timeout=%ds", url, timeout)
        _client = QdrantClient(url=url, api_key=api_key, timeout=timeout)
        logger.info("Qdrant connected")
    return _client


def get_collection():
    client = get_client()
    name = _get_collection_name()
    if not client.collection_exists(collection_name=name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection — name=%s", name)

    try:
        client.create_payload_index(
            collection_name=name,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass

    for field in ["filename", "section"]:
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass

    try:
        client.create_payload_index(
            collection_name=name,
            field_name="page_number",
            field_schema=PayloadSchemaType.INTEGER,
        )
    except Exception:
        pass

    return name


def add_documents(
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> dict:
    from .embeddings import get_embeddings

    name = get_collection()
    embeddings_model = get_embeddings()
    client = get_client()
    batch_size = int(os.getenv("QDRANT_BATCH_SIZE", "50"))
    total = len(documents)
    max_retries = 3
    logger.info("Adding %d documents to Qdrant (batch_size=%d)", total, batch_size)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_docs = documents[start:end]
        batch_metas = metadatas[start:end]
        batch_ids = ids[start:end]

        vectors = embeddings_model.embed_documents(batch_docs)

        points = []
        for i, vec in enumerate(vectors):
            payload = {
                "text": batch_docs[i],
                "_string_id": batch_ids[i],
                "metadata": dict(batch_metas[i]),
            }
            payload.update(batch_metas[i])
            points.append(
                PointStruct(
                    id=_to_uuid(batch_ids[i]),
                    vector=vec,
                    payload=payload,
                )
            )

        for attempt in range(max_retries):
            try:
                client.upsert(collection_name=name, points=points)
                logger.debug("Batch %d-%d added (attempt %d)", start, end, attempt + 1)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.warning(
                        "Upsert failed (attempt %d/%d) — retrying in %ds: %s",
                        attempt + 1, max_retries, delay, e,
                    )
                    time.sleep(delay)
                else:
                    logger.error("Upsert failed after %d attempts — batch %d-%d: %s", max_retries, start, end, e)
                    raise

    count = get_doc_count()
    global _version
    _version += 1
    logger.info("Documents added — new_total=%d, version=%d", count, _version)
    return {"count": count}


def query_documents(
    query_text: str,
    n_results: int = 5,
    doc_ids: list[str] | None = None,
) -> dict:
    from .embeddings import get_embeddings

    name = get_collection()
    embeddings_model = get_embeddings()
    client = get_client()

    query_vector = embeddings_model.embed_query(query_text)

    search_filter = None
    if doc_ids:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="doc_id",
                    match=MatchAny(any=doc_ids),
                )
            ]
        )

    logger.debug(
        "Qdrant query — n=%d, filter=%s, q=%s",
        n_results, search_filter, query_text[:50],
    )

    results = client.query_points(
        collection_name=name,
        query=query_vector,
        limit=n_results,
        query_filter=search_filter,
        with_payload=True,
    )

    points = results.points
    hit_count = len(points)
    min_score = min(p.score for p in points) if points else None
    max_score = max(p.score for p in points) if points else None
    logger.debug(
        "Qdrant results — hits=%d, min_score=%.4f, max_score=%.4f",
        hit_count, min_score or 0, max_score or 0,
    )

    documents = []
    metadatas = []
    distances = []
    for hit in points:
        payload = dict(hit.payload) if hit.payload else {}
        text = payload.pop("text", "")
        documents.append(text)
        metadatas.append(payload)
        distances.append(1 - hit.score)

    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


def get_doc_count() -> int:
    client = get_client()
    name = _get_collection_name()
    try:
        info = client.get_collection(collection_name=name)
        return int(info.points_count or 0)
    except Exception:
        return 0


def get_version() -> int:
    return _version


def delete_by_doc_id(doc_id: str) -> int:
    """Delete all chunks for a given doc_id. Returns number of chunks removed."""
    client = get_client()
    name = _get_collection_name()

    try:
        count_before = get_doc_count()
        client.delete(
            collection_name=name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
                ]
            ),
        )
        count_after = get_doc_count()
        deleted = count_before - count_after
        logger.info("Deleted %d chunks for doc_id=%s", deleted, doc_id)
    except Exception as e:
        logger.warning("Delete failed for doc_id=%s: %s", doc_id, e)
        deleted = 0

    global _version
    _version += 1

    return deleted


def reset_collection() -> None:
    """Delete and recreate the collection."""
    global _client, _collection_name, _version
    client = get_client()
    name = _get_collection_name()
    try:
        client.delete_collection(collection_name=name)
        logger.info("Deleted old collection — name=%s", name)
    except Exception:
        logger.debug("Collection %s did not exist", name)

    _collection_name = None
    _version += 1

    get_collection()
    logger.info("Recreated collection — name=%s", _get_collection_name())
