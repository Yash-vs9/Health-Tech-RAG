"""
Message service.

Stores each Q&A turn in a chat session. The actual RAG call
(retrieval + LLM) happens in the main repo's query_engine.py —
this service just persists the conversation.
"""
from __future__ import annotations

from backend.db.supabase_client import get_admin_client
from backend.logging_config import get_logger

logger = get_logger("backend.messages")


def add_message(
    chat_session_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> dict:
    client = get_admin_client()
    result = client.table("messages").insert({
        "chat_session_id": chat_session_id,
        "role": role,
        "content": content,
        "sources": sources,
    }).execute()

    row = result.data[0]
    logger.debug("Message added — chat=%s, role=%s, len=%d", chat_session_id, role, len(content))
    return row


def get_chat_history(user_id: str, chat_session_id: str) -> list[dict]:
    """
    Returns messages only if the chat session belongs to user_id —
    enforced here explicitly since we use the admin client (bypasses RLS).
    """
    client = get_admin_client()

    session_check = client.table("chat_sessions") \
        .select("id") \
        .eq("id", chat_session_id) \
        .eq("user_id", user_id) \
        .maybe_single() \
        .execute()

    if not session_check or not session_check.data:
        raise ValueError("Chat session not found or not owned by user")

    result = client.table("messages") \
        .select("*") \
        .eq("chat_session_id", chat_session_id) \
        .order("created_at", desc=False) \
        .execute()

    return result.data


def build_conversation_context(messages: list[dict], max_turns: int = 5) -> str:
    """
    Optional helper: formats recent chat history into a string that can be
    prepended to the RAG prompt for follow-up question support
    (e.g. "what about the second one?" referring to a prior answer).
    """
    recent = messages[-(max_turns * 2):]
    lines = []
    for m in recent:
        prefix = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{prefix}: {m['content']}")
    return "\n".join(lines)
