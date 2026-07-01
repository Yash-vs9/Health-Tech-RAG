from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from backend.models.schemas import DocumentResponse
from backend.services import auth_service, document_service, session_service, ingestion
from backend.services import vectorstore
from backend.logging_config import get_logger

logger = get_logger("backend.routes.documents")

router = APIRouter(prefix="/chats/{chat_session_id}/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("", response_model=DocumentResponse)
async def upload_document(
    chat_session_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(auth_service.get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Only PDF and DOCX files are accepted. Got: {ext}")

    session = session_service.get_chat_session(user["id"], chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    file_bytes = await file.read()

    # Step 1: Create DB row (status=processing)
    row = document_service.create_document_row(
        user_id=user["id"],
        chat_session_id=chat_session_id,
        filename=file.filename,
        file_size=len(file_bytes),
    )

    # Step 2: Ingest into ChromaDB
    try:
        result = ingestion.ingest_document(
            file_bytes=file_bytes,
            filename=file.filename,
            doc_id=row["doc_id"],
        )
    except Exception as e:
        logger.error("Ingestion failed — doc_id=%s, error=%s", row["doc_id"], e)
        document_service.mark_document_failed(row["id"], str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    # Step 3: Upload to Supabase Storage only after ingestion succeeds
    try:
        document_service.upload_to_storage(
            user_id=user["id"],
            doc_id=row["doc_id"],
            filename=file.filename,
            file_bytes=file_bytes,
        )
        document_service.mark_document_ready(row["id"], result["num_chunks"])
    except Exception as e:
        logger.error("Storage upload failed — doc_id=%s, error=%s", row["doc_id"], e)
        document_service.mark_document_failed(row["id"], str(e))
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    return row


@router.get("", response_model=list[DocumentResponse])
async def list_documents(chat_session_id: str, user: dict = Depends(auth_service.get_current_user)):
    return document_service.list_documents(user["id"], chat_session_id)


@router.delete("/{document_id}")
async def delete_document(chat_session_id: str, document_id: str, user: dict = Depends(auth_service.get_current_user)):
    try:
        row = document_service.delete_document(user["id"], document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Integration: remove vectors from ChromaDB
    try:
        vectorstore.delete_by_doc_id(row["doc_id"])
    except Exception as e:
        logger.warning("ChromaDB cleanup failed — doc_id=%s, error=%s", row["doc_id"], e)

    return {"status": "deleted", "doc_id": row["doc_id"]}
