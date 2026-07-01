from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from backend.models.schemas import DocumentResponse
from backend.services import auth_service, document_service, session_service
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
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Only PDF and DOCX files are accepted. Got: {ext}")

    # Verify the chat session belongs to this user before allowing upload
    session = session_service.get_chat_session(user["id"], chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    file_bytes = await file.read()
    row = document_service.upload_document(
        user_id=user["id"],
        chat_session_id=chat_session_id,
        filename=file.filename,
        file_bytes=file_bytes,
    )

    # ── INTEGRATION POINT ────────────────────────────────────────────────
    # Call the main repo's ingestion pipeline here, using row["doc_id"]
    # as the doc_id so ChromaDB metadata matches this Postgres row:
    #
    #   from backend.services import ingestion  # main repo's module
    #   result = ingestion.ingest_document(
    #       file_bytes=file_bytes,
    #       filename=file.filename,
    #       doc_id=row["doc_id"],   # <- requires adding doc_id param upstream
    #   )
    #   document_service.mark_document_ready(row["id"], result["num_chunks"])
    #
    # Until that's wired in, status stays 'processing'.
    # ─────────────────────────────────────────────────────────────────────

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

    # ── INTEGRATION POINT ────────────────────────────────────────────────
    # Also remove vectors from ChromaDB so deleted docs stop being retrieved:
    #
    #   from backend.services import vectorstore  # main repo's module
    #   vectorstore.delete_by_doc_id(row["doc_id"])
    # ─────────────────────────────────────────────────────────────────────

    return {"status": "deleted", "doc_id": row["doc_id"]}
