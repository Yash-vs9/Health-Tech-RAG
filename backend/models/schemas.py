from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    full_name: Optional[str] = None


class GoogleOAuthURLResponse(BaseModel):
    auth_url: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    created_at: datetime


# ── Chat Sessions ─────────────────────────────────────────────────────────

class CreateChatSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


class RenameChatSessionRequest(BaseModel):
    title: str


# ── Documents ─────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    chat_session_id: str
    filename: str
    doc_id: str
    num_chunks: int
    status: str
    file_size_bytes: Optional[int] = None
    uploaded_at: datetime


# ── Messages ──────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    chat_session_id: str
    question: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[list[dict[str, Any]]] = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    chat_session_id: str
    title: str
    messages: list[MessageResponse]
    documents: list[DocumentResponse]
