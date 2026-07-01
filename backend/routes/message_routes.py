from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import SendMessageRequest, MessageResponse, ChatHistoryResponse
from backend.services import auth_service, message_service, session_service, document_service, query_engine
from backend.logging_config import get_logger

logger = get_logger("backend.routes.messages")

router = APIRouter(prefix="/chats/{chat_session_id}/messages", tags=["messages"])


@router.post("", response_model=MessageResponse)
async def send_message(
    chat_session_id: str,
    req: SendMessageRequest,
    user: dict = Depends(auth_service.get_current_user),
):
    session = session_service.get_chat_session(user["id"], chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    prior_messages = message_service.get_chat_history(user["id"], chat_session_id)
    conversation_context = message_service.build_conversation_context(prior_messages)

    # 1. Store the user's question
    message_service.add_message(chat_session_id, role="user", content=req.question)

    # 2. Run RAG scoped to this chat's documents
    docs = document_service.list_documents(user["id"], chat_session_id)
    doc_ids = [d["doc_id"] for d in docs if d["status"] == "ready"]

    result = query_engine.query_rag(
        question=req.question,
        doc_ids=doc_ids if doc_ids else None,
        conversation_context=conversation_context,
    )
    answer, sources = result["answer"], result["sources"]

    # 3. Store the assistant's answer
    assistant_msg = message_service.add_message(
        chat_session_id, role="assistant", content=answer, sources=sources,
    )

    return assistant_msg


@router.get("", response_model=ChatHistoryResponse)
async def get_history(chat_session_id: str, user: dict = Depends(auth_service.get_current_user)):
    session = session_service.get_chat_session(user["id"], chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    try:
        messages = message_service.get_chat_history(user["id"], chat_session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    documents = document_service.list_documents(user["id"], chat_session_id)

    return {
        "chat_session_id": chat_session_id,
        "title": session["title"],
        "messages": messages,
        "documents": documents,
    }
