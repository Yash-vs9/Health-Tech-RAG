from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import (
    CreateChatSessionRequest, ChatSessionResponse, RenameChatSessionRequest,
)
from backend.services import auth_service, session_service

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
        session_service.delete_chat_session(user["id"], chat_session_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
