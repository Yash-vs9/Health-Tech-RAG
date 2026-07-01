# Auth & Session Service

User authentication, chat session management, document upload/delete, and chat history persistence — the complete user-facing layer built on top of the existing Mortgage/Health-Tech RAG pipeline.

**Stack:** FastAPI + Supabase (Auth + PostgreSQL + Storage) — all free tier.

---

## What We Built

### 1. User Authentication
- Email + password signup and login
- Google OAuth (Sign in with Google)
- JWT token verification on every protected route
- Auto-logout, token refresh
- User profile auto-created on first signup (triggered by DB)

### 2. Chat Sessions
- User can create multiple chat sessions ("New Chat")
- Each session can hold multiple uploaded documents
- Sessions can be renamed and deleted
- Deleting a session auto-deletes all its documents and messages (DB cascade)
- Sessions listed newest-first, with document count per session

### 3. Document Management
- Upload PDF or DOCX into a specific chat session
- File stored in Supabase Storage (not local disk — survives redeploy)
- Each doc gets a unique `doc_id` that links to ChromaDB vectors in main repo
- Soft delete — file removed from Storage, row marked `deleted` in DB
- `doc_id` returned on delete so ChromaDB vectors can be cleaned up

### 4. Chat History + Memory
- Every question (user) and answer (assistant) stored in DB per session
- Full history retrievable per chat — powers sidebar "past chats" view
- `build_conversation_context()` formats last 5 turns so follow-up questions work
  ("what about the second one?" — bot knows what first one was)

### 5. Security
- Row Level Security on every DB table — users can never access each other's data
- Storage bucket restricted per user_id prefix
- Service role key (bypasses RLS) used only server-side, never exposed to frontend
- Passwords never touched — Supabase Auth handles hashing

---

## File-by-File Explanation

### `sql/schema.sql`
The entire database setup — run this once in Supabase SQL Editor.

Creates 4 tables:
- `profiles` — one row per user, auto-created when they sign up (via DB trigger `handle_new_user`). Stores name, email, avatar, OAuth provider.
- `chat_sessions` — one row per "New Chat". Linked to user. Has title, created_at, updated_at (updated_at auto-bumped on every new message via trigger `touch_chat_session`).
- `documents` — one row per uploaded file. Linked to chat_session. Stores filename, storage path in Supabase, doc_id (matches ChromaDB), status (`processing` → `ready` → `deleted`), chunk count.
- `messages` — one row per message turn. Linked to chat_session. Stores role (`user`/`assistant`), content, sources (JSON — citation chunks from RAG).

Also creates:
- Row Level Security policies on all 4 tables
- Private `documents` storage bucket with per-user access policies
- Two DB triggers (auto-create profile, auto-bump updated_at)

---

### `backend/main.py`
FastAPI app entry point.

- Loads `.env` first (dotenv)
- Sets up CORS so frontend (localhost:3000) can talk to backend (localhost:8001)
- Registers all 4 routers (auth, chats, documents, messages)
- Single `/health` endpoint for uptime check

Run with:
```bash
uvicorn backend.main:app --reload --port 8001
```

---

### `backend/db/supabase_client.py`
Two Supabase clients, both cached with `@lru_cache`:

- `get_anon_client()` — uses anon/public key. Respects Row Level Security. Used for auth operations (signup/login) where user not yet authenticated.
- `get_admin_client()` — uses service_role key. **Bypasses RLS.** Used by backend for trusted server-side DB operations. **Never expose this key to frontend.**

---

### `backend/models/schemas.py`
All Pydantic request/response models. Every API endpoint uses these for validation and serialization.

Key models:
- `SignupRequest` — email (validated), password (min 8 chars), optional full_name
- `LoginRequest` — email + password
- `AuthResponse` — access_token, refresh_token, user_id, email, full_name
- `CreateChatSessionRequest` — optional title (defaults to "New Chat")
- `ChatSessionResponse` — id, title, timestamps, document_count
- `DocumentResponse` — id, filename, doc_id, status, num_chunks, uploaded_at
- `MessageResponse` — id, role, content, sources (list of citation dicts), created_at
- `ChatHistoryResponse` — full session with messages + documents combined

---

### `backend/services/auth_service.py`
Core auth logic. Wraps Supabase Auth SDK.

Functions:
- `signup_with_email(email, password, full_name)` — creates user in Supabase Auth. Returns tokens if email confirmation disabled, else returns `requires_email_confirmation: True`.
- `login_with_email(email, password)` — validates credentials, returns JWT access_token + refresh_token.
- `refresh_session(refresh_token)` — exchanges expired access_token for new one using refresh_token.
- `logout(access_token)` — invalidates session on Supabase side.
- `get_google_oauth_url(redirect_to)` — returns URL to redirect browser to for Google consent screen. Supabase handles the OAuth dance and redirects back with tokens.
- `get_current_user(authorization)` — **FastAPI dependency**. Extracts Bearer token from header, verifies it with Supabase, returns `{id, email, full_name}`. Used on every protected route with `Depends(get_current_user)`.

---

### `backend/services/session_service.py`
Chat session CRUD. All operations scoped to user_id.

Functions:
- `create_chat_session(user_id, title)` — inserts new row, returns it with document_count=0.
- `list_chat_sessions(user_id)` — returns all sessions newest-first. Counts non-deleted documents per session in one extra query (avoids N+1).
- `get_chat_session(user_id, chat_session_id)` — single session lookup, verifies ownership.
- `rename_chat_session(user_id, chat_session_id, title)` — updates title, raises ValueError if not found/not owned.
- `delete_chat_session(user_id, chat_session_id)` — deletes row. DB cascade handles documents + messages automatically.

---

### `backend/services/document_service.py`
Document upload, status tracking, and deletion.

Functions:
- `upload_document(user_id, chat_session_id, filename, file_bytes)` — generates unique `doc_id`, uploads raw file bytes to Supabase Storage at path `{user_id}/{doc_id}_{filename}`, creates DB row with status=`processing`. Returns row. Caller must trigger RAG ingestion separately (see INTEGRATION POINT).
- `mark_document_ready(document_row_id, num_chunks)` — called after ingestion succeeds. Updates status to `ready` and stores chunk count.
- `mark_document_failed(document_row_id, error)` — called if ingestion fails. Updates status to `failed`.
- `list_documents(user_id, chat_session_id)` — returns all non-deleted docs for a session, oldest-first.
- `delete_document(user_id, document_id)` — removes file from Supabase Storage, marks row as `deleted`. Returns the row (including `doc_id`) so caller can remove vectors from ChromaDB.

---

### `backend/services/message_service.py`
Chat history persistence.

Functions:
- `add_message(chat_session_id, role, content, sources)` — inserts one message row. Role is `user` or `assistant`. Sources is list of citation dicts (chunk text, doc name, page number etc).
- `get_chat_history(user_id, chat_session_id)` — verifies session ownership, returns all messages ordered by created_at (oldest first = correct conversation order).
- `build_conversation_context(messages, max_turns=5)` — formats last 10 messages (5 turns) into a string like:
  ```
  User: what is the interest rate?
  Assistant: The interest rate is 8.5% per annum...
  User: what about the processing fee?
  ```
  This string is passed to the RAG LLM so it understands follow-up questions.

---

### `backend/routes/auth_routes.py`
REST endpoints for authentication.

| Endpoint | What it does |
|---|---|
| `POST /auth/signup` | Create account with email+password |
| `POST /auth/login` | Login, get tokens |
| `POST /auth/refresh` | Get new access_token using refresh_token |
| `GET /auth/google/url?redirect_to=...` | Get Google OAuth URL for frontend redirect |
| `POST /auth/logout` | Logout (requires token) |
| `GET /auth/me` | Get own profile (requires token) |

---

### `backend/routes/chat_routes.py`
REST endpoints for chat session management.

| Endpoint | What it does |
|---|---|
| `POST /chats` | Create new chat session |
| `GET /chats` | List all my chats (newest first) |
| `GET /chats/{id}` | Get one chat |
| `PATCH /chats/{id}` | Rename a chat |
| `DELETE /chats/{id}` | Delete chat + all its docs + messages |

All require `Authorization: Bearer <token>` header.

---

### `backend/routes/document_routes.py`
REST endpoints for document upload/delete inside a chat.

| Endpoint | What it does |
|---|---|
| `POST /chats/{id}/documents` | Upload PDF or DOCX into chat |
| `GET /chats/{id}/documents` | List documents in chat |
| `DELETE /chats/{id}/documents/{doc_id}` | Delete document from Storage + mark deleted |

**INTEGRATION POINT 1** (after upload): call `ingestion.ingest_document()` with same `doc_id` so ChromaDB metadata matches DB.

**INTEGRATION POINT 2** (after delete): call `vectorstore.delete_by_doc_id(row["doc_id"])` to clean ChromaDB — Lakshya needs to add this function to `vectorstore.py`.

---

### `backend/routes/message_routes.py`
REST endpoints for sending questions and retrieving chat history.

| Endpoint | What it does |
|---|---|
| `POST /chats/{id}/messages` | Send a question, get answer |
| `GET /chats/{id}/messages` | Get full chat history for this session |

`POST /chats/{id}/messages` flow:
1. Pulls prior conversation history for this chat
2. Formats last 5 turns into `conversation_context` string
3. Stores user question in DB
4. **INTEGRATION POINT 3**: calls `query_engine.query_rag(question, doc_ids, conversation_context)` — currently stubbed, uncomment when wiring into main repo
5. Stores assistant answer + sources in DB
6. Returns the assistant message

---

### `backend/logging_config.py`
Simple logging setup. Reads `LOG_LEVEL` from env (default INFO). Format:
```
2026-07-01 10:30:00 | INFO     | backend.auth | User logged in — id=abc123
```

---

### `.env.example`
Template for environment variables. Copy to `.env` and fill in:
- `SUPABASE_URL` — from Supabase Dashboard → Settings → API
- `SUPABASE_ANON_KEY` — safe to use in frontend
- `SUPABASE_SERVICE_ROLE_KEY` — backend only, never commit to git
- `SUPABASE_STORAGE_BUCKET` — default `documents`
- `FRONTEND_URL` — for CORS (default `http://localhost:3000`)

---

### `requirements.txt`
```
fastapi          — web framework
uvicorn          — ASGI server
python-multipart — file upload support
pydantic[email]  — request/response validation + email validation
python-dotenv    — loads .env file
supabase         — Supabase Python SDK (Auth + DB + Storage)
```

---

### `tests/test_auth_api.py`
5 tests, all pass without needing a real Supabase project:

1. `test_health_endpoint` — GET /health returns 200 ok
2. `test_signup_requires_valid_email` — bad email → 422 validation error
3. `test_signup_requires_min_password_length` — password < 8 chars → 422
4. `test_protected_route_without_token_returns_401` — GET /chats no token → 401
5. `test_protected_route_with_garbage_token_returns_401` — fake token → 401

Run with:
```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Setup (5 Steps)

### Step 1 — Create Supabase project
[supabase.com](https://supabase.com) → New Project → free tier

### Step 2 — Run schema
Dashboard → SQL Editor → New Query → paste `sql/schema.sql` → Run

### Step 3 — Enable Google OAuth
Dashboard → Authentication → Providers → Google → toggle on → add Client ID + Secret from Google Cloud Console

### Step 4 — Set up .env
```bash
cp .env.example .env
# fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
```

### Step 5 — Run
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8001
# open http://localhost:8001/docs
```

---

## Integration Points (3 spots to wire into main repo)

| # | File | What to do |
|---|---|---|
| 1 | `document_routes.py` after upload | Call `ingestion.ingest_document(file_bytes, filename, doc_id=row["doc_id"])` — needs `doc_id` param added to main repo's ingestion |
| 2 | `document_routes.py` after delete | Call `vectorstore.delete_by_doc_id(row["doc_id"])` — Lakshya needs to add this function |
| 3 | `message_routes.py` send_message | Replace stub with `query_engine.query_rag(question, doc_ids, conversation_context)` — needs `conversation_context` param added upstream |

---

## Data Flow (Full Picture)

```
User opens app
    │
    ▼
POST /auth/login  ──→  Supabase Auth  ──→  JWT token returned
    │
    ▼
POST /chats  ──→  new chat_session row created in Postgres
    │
    ▼
POST /chats/{id}/documents  ──→  file uploaded to Supabase Storage
                             ──→  documents row created (status=processing)
                             ──→  [INTEGRATION] ingest_document() called
                             ──→  vectors stored in ChromaDB
                             ──→  mark_document_ready() called (status=ready)
    │
    ▼
POST /chats/{id}/messages  ──→  prior history fetched from DB
                            ──→  user message stored
                            ──→  [INTEGRATION] query_rag(question, doc_ids, context)
                            ──→  assistant answer + sources stored
                            ──→  answer returned to frontend
    │
    ▼
GET /chats/{id}/messages  ──→  full conversation history from DB
    │
    ▼
DELETE /chats/{id}/documents/{doc_id}  ──→  file deleted from Storage
                                        ──→  [INTEGRATION] delete_by_doc_id() called
                                        ──→  vectors removed from ChromaDB
                                        ──→  row marked deleted in DB
```
