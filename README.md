# Mortgage RAG Chatbot

> RAG system for mortgage document Q&A, summarization, and cross-document comparison
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Pipeline Architecture

```
User Upload (PDF / DOCX)
         |
         v
    POST /chats/{id}/documents  -->  Document Loader  -->  Text Splitter (512/50)  -->  Qwen3-Embedding-8B (4096-dim)
                                                                                           |
                                                                                           v
                                                                                 ChromaDB Vector Store
                                                                                           |
                                                                                           v
User Question  -->  POST /chats/{id}/messages  -->  Hybrid Retriever  -->  LLM  -->  Answer + Sources
                                           |
                             +-------------+-------------+
                             |             |             |
                         BM25        Vector (k=5)   Multi-Query
                       Keyword       ChromaDB       Generate N
                       Search        Cosine         reformulations
                             |             |             |
                             +------+------+------+------+
                                    |
                             Reciprocal Rank
                               Fusion (RRF)
                                    |
                                    v
                            Top 5 Fused Results
                                                                                     |
                                                                            +---------+---------+---------+---------+
                                                                            |         |         |                   |
                                                                             LLM_PROVIDER LLM_PROVIDER LLM_PROVIDER    LLM_PROVIDER
                                                                           = ollama     = gemini     = hf            = nvidia
                                                                         llama3.2   gemini-2.5-flash-lite Qwen2.5-7B  nemotron-nano-9b-v2
                                                                            |         |         |                   |
                                                                            +---------+---------+---------+---------+
                                                                                    |
                                                                                    v
                                                                              React Frontend
```

---

## Directory Structure

```
Health-Tech-RAG/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app — health, auth, chats, documents, messages
│   ├── schemas.py               # Pydantic request/response models
│   ├── logging_config.py        # Centralized logging (console + file)
│   ├── db/
│   │   └── supabase_client.py   # Supabase anon + admin clients
│   ├── models/
│   │   └── schemas.py           # Auth, session, document, message models
│   ├── routes/
│   │   ├── auth_routes.py       # POST /auth/signup, /login, /logout, /me, /google/url
│   │   ├── chat_routes.py       # CRUD for /chats
│   │   ├── document_routes.py   # Upload/list/delete documents in a chat
│   │   └── message_routes.py    # Send message + get chat history
│   └── services/
│       ├── __init__.py
│       ├── llm.py               # LLM provider (Ollama / Gemini / HuggingFace / NVIDIA)
│       ├── embeddings.py        # Qwen3-Embedding-8B (4096-dim) via HuggingFace API
│       ├── vectorstore.py       # ChromaDB integration with embedding function
│       ├── ingestion.py         # PDF + DOCX → chunk → embed → store
│       ├── retriever.py         # Hybrid: BM25 + Vector + Multi-Query + RRF
│       ├── query_engine.py      # RAG: retrieve context → LLM → answer
│       ├── auth_service.py      # Supabase auth (email/password + Google OAuth)
│       ├── session_service.py   # Chat session CRUD
│       ├── document_service.py  # Upload to Supabase Storage, status tracking
│       └── message_service.py   # Chat history, conversation context
├── frontend/                    # React app (Vite + Tailwind)
│   ├── package.json
│   ├── vite.config.js           # Proxy to backend:8001
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Routes: Home, Login, Signup, Dashboard
│       ├── App.css
│       ├── api.js               # API client (auth, chats, docs, messages)
│       ├── context/
│       │   └── AuthContext.jsx   # Auth state (token, user)
│       ├── pages/
│       │   ├── Home.jsx         # Landing page
│       │   ├── Login.jsx        # Login form
│       │   ├── Signup.jsx       # Signup form
│       │   └── Dashboard.jsx    # Main app (chats + chat view)
│       └── components/
│           ├── ChatList.jsx     # Sidebar with chat sessions
│           ├── ChatView.jsx     # Chat messages + file upload
│           ├── Chatbox.jsx      # Chat input box
│           ├── FileUpload.jsx   # PDF/DOCX upload
│           ├── Navbar.jsx       # Navigation bar
│           ├── Sidebar.jsx      # Side panel
│           ├── FeatureCard.jsx  # Feature cards
│           └── TeamCard.jsx     # Team member cards
├── sql/
│   └── schema.sql               # Supabase schema (profiles, sessions, documents, messages + RLS)
├── prompts/
│   └── health_system_prompt.txt # System prompt with few-shot examples
├── tests/
│   ├── backend/
│   │   └── test_retriever.py    # Chunk dedup tests
│   └── evaluation/
│       ├── documents/           # Mortgage PDFs for evaluation
│       ├── golden_datasets/     # Golden dataset JSONs (275 questions)
│       └── evaluate.py          # RAGAS evaluation script
├── data/
│   ├── uploaded_pdfs/           # Uploaded documents (local)
│   └── chroma_db/               # Persistent ChromaDB
├── requirements.txt
├── .env.example
├── logs.bat                     # View/tail logs from project directory
└── README.md
```

---

## Quick Start

### 1. Backend Setup

```bash
git clone https://github.com/<org>/Health-Tech-RAG.git
cd Health-Tech-RAG
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Required env vars:

```env
# LLM (pick one)
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=your_nvidia_key

# Embeddings (required)
HUGGINGFACEHUB_API_TOKEN=your_hf_token

# Supabase (required for auth + chat sessions)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=documents
```

### 3. Setup Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run `sql/schema.sql` in the SQL Editor
3. Create a storage bucket named `documents`
4. Copy your project URL and keys to `.env`

### 4. Start Backend

```bash
uvicorn backend.main:app --reload --port 8001
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## Configuration Options

### LLM Provider

| `LLM_PROVIDER` | Model | Requires | Cost |
|----------------|-------|----------|------|
| `ollama` | llama3.2 | Ollama installed locally | Free |
| `gemini` | gemini-2.5-flash-lite | `GOOGLE_API_KEY` | Free tier |
| `hf` | Qwen/Qwen2.5-7B-Instruct | `HUGGINGFACEHUB_API_TOKEN` | Free tier |
| `nvidia` | nemotron-nano-9b-v2 | `NVIDIA_API_KEY` | Free tier |

### Embedding Model

| Model | Dimensions | Requires | Cost |
|-------|-----------|----------|------|
| Qwen3-Embedding-8B | 4096 | `HUGGINGFACEHUB_API_TOKEN` | Free tier |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Console log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

Logs write to `~/.mortgage-rag/logs/rag_YYYYMMDD.log` (outside project to avoid watchfiles reload loop).

**View logs from project directory:**
```bash
logs.bat           # show today's full log
logs.bat tail      # follow live (like tail -f)
logs.bat dir       # open log folder in explorer
```

**What's logged at each level:**

| Level | What you see |
|-------|-------------|
| `INFO` | Request lifecycle, ingestion progress, LLM provider init, retrieval stats |
| `DEBUG` | Chunk RRF scores, BM25/vector hit counts, prompt token count, ChromaDB distances |

### Retriever Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MULTI_QUERY_ENABLED` | `true` | Generate N reformulated queries for better recall |
| `MULTI_QUERY_N` | `3` | Number of reformulated queries per question |
| `RETRIEVER_TOP_K` | `10` | Number of chunks retrieved and sent to LLM |

---

## API Endpoints

### Auth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account (email + password) |
| `/auth/login` | POST | Login, returns JWT |
| `/auth/logout` | POST | Invalidate session |
| `/auth/me` | GET | Get current user |
| `/auth/google/url` | GET | Get Google OAuth URL |

### Chats

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats` | GET | List all chat sessions |
| `/chats` | POST | Create new chat session |
| `/chats/{id}` | PATCH | Rename chat |
| `/chats/{id}` | DELETE | Delete chat + all documents + ChromaDB chunks + Storage + local files |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats/{id}/documents` | GET | List documents in chat |
| `/chats/{id}/documents` | POST | Upload PDF/DOCX → ingest → store |
| `/chats/{id}/documents/{doc_id}` | DELETE | Delete document ( ChromaDB + Storage + local file) |

### Messages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats/{id}/messages` | POST | Send question → RAG answer |
| `/chats/{id}/messages` | GET | Get chat history |

### Legacy (no auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + provider info |
| `/ingest` | POST | Upload and ingest a document |
| `/query` | POST | RAG query without chat context |
| `/reset-collection` | POST | Wipe and recreate ChromaDB collection |

---

## Frontend Features

- **Auth** — Login/Signup with email + Google OAuth
- **Dashboard** — Chat list sidebar + chat view
- **File Upload** — drag-and-drop or click to browse, accepts PDF and DOCX
- **Chat Interface** — ask questions about uploaded mortgage documents
- **Source Citations** — expandable source chunks for each answer
- **Chat History** — persistent messages across sessions
- **Auto-scroll** — chat scrolls to latest message

## Use Cases

- **Loan Officers** — quick lookup of loan terms, rates, and conditions across documents
- **Compliance Teams** — verify RESPA disclosures, check regulatory adherence
- **Cross-Document Comparison** — compare terms across multiple loan agreements
- **Summarization** — get concise summaries of lengthy appraisal reports

---

## RAGAS Evaluation

**Structure:**
```
tests/evaluation/
├── documents/        ← Upload mortgage PDFs/DOCXs here
├── golden_datasets/  ← Golden dataset JSONs (275 questions)
└── evaluate.py       ← Evaluation script
```

**Steps:**
1. Upload mortgage documents to `tests/evaluation/documents/`
2. Add golden dataset JSONs to `tests/evaluation/golden_datasets/`
3. Run evaluation:

```bash
python -m tests.evaluation.evaluate
```

**What it does:**
1. Ingests all docs from `documents/`
2. Loads all Q&A pairs from `golden_datasets/`
3. Runs RAG pipeline on each question
4. Evaluates with RAGAS metrics
5. Saves report to `docs/eval_report.md`

**Metrics:**
| Metric | Target | What It Measures |
|--------|--------|------------------|
| Faithfulness | > 0.8 | Answer grounded in retrieved context |
| Answer Relevancy | > 0.75 | Answer addresses the question |
| Context Precision | > 0.7 | Retrieved chunks are relevant |

---

## Important Rules

1. **Never hardcode API keys** — use `.env`
2. **Always set chunk_overlap=50** — never 0
3. **Commit daily** — no version control = risk
4. **Test retrieval before building generation**
5. **Target RAGAS faithfulness > 0.8 before Week 3**

---

*AIforAll Global — Mortgage RAG Team — Week 2 — June 2026*
