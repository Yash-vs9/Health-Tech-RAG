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
    recent = messages[-(max_turns * 2):]
    lines = []
    
    # Calculate feedback summary
    liked = sum(1 for m in recent if m["role"] == "assistant" and m.get("feedback") == "up")
    disliked = sum(1 for m in recent if m["role"] == "assistant" and m.get("feedback") == "down")
    
    for m in recent:
        prefix = "User" if m["role"] == "user" else "Assistant"
        line = f"{prefix}: {m['content']}"
        # Include explicit feedback token
        if m["role"] == "assistant" and m.get("feedback"):
            if m["feedback"] == "up":
                line += "\n\n[USER_RATING: POSITIVE - User found this answer helpful. Maintain this style and format.]"
            else:
                line += "\n\n[USER_RATING: NEGATIVE - User found this answer unhelpful. Adjust approach: check for missing sources, reduce verbosity, or clarify information.]"
        lines.append(line)
    
    context = "\n\n".join(lines)
    
    # Add feedback summary if there's any feedback
    if liked + disliked > 0:
        context = f"[CONVERSATION_FEEDBACK_SUMMARY: {liked} liked, {disliked} disliked answers in this conversation]\n\n{context}"
    
    return context

def update_message_feedback(
    user_id: str,
    chat_session_id: str,
    message_id: str,
    feedback: str | None,
) -> dict:
    """
    feedback must be 'up', 'down', or None (to clear it).
    Verifies the chat session belongs to the user before updating.
    """
    if feedback not in ("up", "down", None):
        raise ValueError("feedback must be 'up', 'down', or null")

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
        .update({"feedback": feedback}) \
        .eq("id", message_id) \
        .eq("chat_session_id", chat_session_id) \
        .execute()

    if not result.data:
        raise ValueError("Message not found")

    logger.debug("Feedback updated — message=%s, feedback=%s", message_id, feedback)
    return result.data[0]