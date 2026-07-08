from __future__ import annotations

import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import (
    CreateChatSessionRequest, ChatSessionResponse, RenameChatSessionRequest,
)
from backend.services import auth_service, session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chat-sessions"])


@router.post("", response_model=ChatSessionResponse)
async def create_chat(req: CreateChatSessionRequest, user: dict = Depends(auth_service.get_current_user)):
    return session_service.create_chat_session(user["id"], req.title or "New Chat")


@router.get("", response_model=list[ChatSessionResponse])
async def list_chats(user: dict = Depends(auth_service.get_current_user)):
    return session_service.list_chat_sessions(user["id"])


@router.get("/{chat_session_id}", response_model=ChatSessionResponse)
async def get_chat(chat_session_id: str, user: dict = Depends(auth_service.get_current_user)):
    session = session_service.get_chat_session(user["id"], chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {**session, "document_count": 0}


@router.patch("/{chat_session_id}", response_model=ChatSessionResponse)
async def rename_chat(chat_session_id: str, req: RenameChatSessionRequest, user: dict = Depends(auth_service.get_current_user)):
    try:
        result = session_service.rename_chat_session(user["id"], chat_session_id, req.title)
        return {**result, "document_count": 0}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{chat_session_id}")
async def delete_chat(chat_session_id: str, user: dict = Depends(auth_service.get_current_user)):
    try:
        # Get all documents for this chat before deleting
        from backend.services import document_service, vectorstore
        documents = document_service.list_documents(user["id"], chat_session_id)

        # Clean up each document: ChromaDB chunks, Supabase Storage, local PDF
        for doc in documents:
            try:
                vectorstore.delete_by_doc_id(doc["doc_id"])
            except Exception as e:
                logger.warning("ChromaDB cleanup failed for doc_id=%s: %s", doc.get("doc_id"), e)

            try:
                if doc.get("storage_path"):
                    from backend.db.supabase_client import get_admin_client
                    get_admin_client().storage.from_(document_service.BUCKET).remove([doc["storage_path"]])
            except Exception as e:
                logger.warning("Storage cleanup failed for doc_id=%s: %s", doc.get("doc_id"), e)

            # Delete local PDF file
            local_path = os.path.join("data", "uploaded_pdfs", f"{doc['doc_id']}_{doc['filename']}")
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info("Deleted local PDF — path=%s", local_path)
            except Exception as e:
                logger.warning("Local file cleanup failed for doc_id=%s: %s", doc.get("doc_id"), e)

            # Mark document as deleted in DB
            try:
                document_service.delete_document(user["id"], doc["id"])
            except Exception as e:
                logger.warning("Document DB delete failed for doc_id=%s: %s", doc.get("doc_id"), e)

        session_service.delete_chat_session(user["id"], chat_session_id)
        return {"status": "deleted", "documents_cleaned": len(documents)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
