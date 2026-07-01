"""
Chat session service.

A chat session belongs to one user and can hold multiple documents.
All queries go through the admin client (service_role) since the backend
has already authenticated the user via the JWT — we pass user_id explicitly
and trust it, rather than relying on RLS here (RLS is the second line of
defense if someone calls Supabase directly).
"""
from __future__ import annotations

from backend.db.supabase_client import get_admin_client
from backend.logging_config import get_logger

logger = get_logger("backend.sessions")


def create_chat_session(user_id: str, title: str = "New Chat") -> dict:
    client = get_admin_client()
    result = client.table("chat_sessions").insert({
        "user_id": user_id,
        "title": title,
    }).execute()

    session = result.data[0]
    logger.info("Chat session created — id=%s, user_id=%s", session["id"], user_id)
    return {**session, "document_count": 0}


def list_chat_sessions(user_id: str) -> list[dict]:
    client = get_admin_client()

    sessions_result = client.table("chat_sessions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()

    sessions = sessions_result.data
    if not sessions:
        return []

    # Get document counts per session in one query
    session_ids = [s["id"] for s in sessions]
    docs_result = client.table("documents") \
        .select("chat_session_id") \
        .in_("chat_session_id", session_ids) \
        .neq("status", "deleted") \
        .execute()

    counts: dict[str, int] = {}
    for d in docs_result.data:
        counts[d["chat_session_id"]] = counts.get(d["chat_session_id"], 0) + 1

    for s in sessions:
        s["document_count"] = counts.get(s["id"], 0)

    logger.debug("Listed chat sessions — user_id=%s, count=%d", user_id, len(sessions))
    return sessions


def get_chat_session(user_id: str, chat_session_id: str) -> dict | None:
    client = get_admin_client()
    result = client.table("chat_sessions") \
        .select("*") \
        .eq("id", chat_session_id) \
        .eq("user_id", user_id) \
        .maybe_single() \
        .execute()
    return result.data if result else None


def rename_chat_session(user_id: str, chat_session_id: str, title: str) -> dict:
    client = get_admin_client()
    result = client.table("chat_sessions") \
        .update({"title": title}) \
        .eq("id", chat_session_id) \
        .eq("user_id", user_id) \
        .execute()

    if not result.data:
        raise ValueError("Chat session not found or not owned by user")

    logger.info("Chat session renamed — id=%s, title=%s", chat_session_id, title)
    return result.data[0]


def delete_chat_session(user_id: str, chat_session_id: str) -> None:
    """
    Deletes the chat session row. Cascades to documents and messages
    via ON DELETE CASCADE in the schema. Does NOT delete files from
    Storage or vectors from ChromaDB — call document_service.delete_document
    for each document first if you need that cleanup.
    """
    client = get_admin_client()
    result = client.table("chat_sessions") \
        .delete() \
        .eq("id", chat_session_id) \
        .eq("user_id", user_id) \
        .execute()

    if not result.data:
        raise ValueError("Chat session not found or not owned by user")

    logger.info("Chat session deleted — id=%s, user_id=%s", chat_session_id, user_id)
