"""
Document service.

Handles the metadata + storage side of document upload/delete.
This does NOT do PDF parsing/chunking/embedding — that's the existing
RAG pipeline's job (backend/services/ingestion.py in the main repo).

Integration point for the team: after this service uploads the file and
creates the `documents` row, call the main repo's `ingestion.ingest_document()`
with the same `doc_id` so ChromaDB metadata and this table's doc_id match up.
That lets delete_document() below clean up both Postgres AND ChromaDB.
"""
from __future__ import annotations

import os
import uuid
from backend.db.supabase_client import get_admin_client
from backend.logging_config import get_logger

logger = get_logger("backend.documents")

BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")


def upload_document(
    user_id: str,
    chat_session_id: str,
    filename: str,
    file_bytes: bytes,
) -> dict:
    """
    1. Uploads the raw file to Supabase Storage under {user_id}/{doc_id}_{filename}
    2. Creates a `documents` row with status='processing'
    3. Returns the row — caller is responsible for triggering ingestion
       (chunking/embedding) and then calling mark_document_ready().
    """
    client = get_admin_client()
    doc_id = str(uuid.uuid4())[:12]
    storage_path = f"{user_id}/{doc_id}_{filename}"

    logger.info(
        "Uploading document — user_id=%s, chat=%s, filename=%s, doc_id=%s",
        user_id, chat_session_id, filename, doc_id,
    )

    client.storage.from_(BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream"},
    )

    result = client.table("documents").insert({
        "chat_session_id": chat_session_id,
        "user_id": user_id,
        "filename": filename,
        "storage_path": storage_path,
        "file_size_bytes": len(file_bytes),
        "doc_id": doc_id,
        "status": "processing",
    }).execute()

    row = result.data[0]
    logger.info("Document row created — id=%s, doc_id=%s", row["id"], doc_id)
    return row


def mark_document_ready(document_row_id: str, num_chunks: int) -> None:
    client = get_admin_client()
    client.table("documents").update({
        "status": "ready",
        "num_chunks": num_chunks,
    }).eq("id", document_row_id).execute()
    logger.info("Document marked ready — id=%s, chunks=%d", document_row_id, num_chunks)


def mark_document_failed(document_row_id: str, error: str) -> None:
    client = get_admin_client()
    client.table("documents").update({"status": "failed"}).eq("id", document_row_id).execute()
    logger.error("Document marked failed — id=%s, error=%s", document_row_id, error)


def list_documents(user_id: str, chat_session_id: str) -> list[dict]:
    client = get_admin_client()
    result = client.table("documents") \
        .select("*") \
        .eq("chat_session_id", chat_session_id) \
        .eq("user_id", user_id) \
        .neq("status", "deleted") \
        .order("uploaded_at", desc=False) \
        .execute()
    return result.data


def delete_document(user_id: str, document_id: str) -> dict:
    """
    Deletes the file from Storage and marks the row as 'deleted'
    (soft delete — keeps doc_id around so ChromaDB cleanup can reference it).

    Returns the deleted row's doc_id so the caller can remove matching
    vectors from ChromaDB: vectorstore.delete_by_doc_id(doc_id)
    """
    client = get_admin_client()

    row_result = client.table("documents") \
        .select("*") \
        .eq("id", document_id) \
        .eq("user_id", user_id) \
        .maybe_single() \
        .execute()

    if not row_result or not row_result.data:
        raise ValueError("Document not found or not owned by user")

    row = row_result.data

    try:
        client.storage.from_(BUCKET).remove([row["storage_path"]])
    except Exception as e:
        logger.warning("Storage delete failed (continuing) — path=%s, error=%s", row["storage_path"], e)

    client.table("documents").update({"status": "deleted"}).eq("id", document_id).execute()
    logger.info("Document deleted — id=%s, doc_id=%s", document_id, row["doc_id"])

    return row
