# Mortgage RAG Chatbot

> RAG system for mortgage document Q&A, summarization, and cross-document comparison
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Pipeline Architecture

```
User Upload (PDF / DOCX / JPG / JPEG / PNG)
         |
         v
    POST /chats/{id}/documents  -->  Document Loader  -->  Text Splitter (512/50)  -->  Qwen3-Embedding-8B (4096-dim)
                                                                                            |
                                                                                    +-------+-------+
                                                                                    |               |
                                                                              ChromaDB         BM25 Index
                                                                              Vector Store     (Keyword)
                                                                                    |               |
                                                                                    +-------+-------+
                                                                                            |
                                                                                  Reciprocal Rank
                                                                                    Fusion (RRF)
                                                                                            |
                                                                                            v
                                                                                    Top 10 Fused Results
                                                                                            |
                                                                                    +-------+-------+
                                                                                    |               |
                                                                              CrossEncoder    Source
                                                                              Reranker        Filter
                                                                                    |               |
                                                                                    +-------+-------+
                                                                                            |
                                                                                    LLM (NVIDIA NIM)
                                                                                    nemotron-nano-9b-v2
                                                                                            |
                                                                                    +-------+-------+
                                                                                    |               |
                                                                              Input           Output
                                                                              Guardrails      Guardrails
                                                                                    |               |
                                                                                    +-------+-------+
                                                                                            |
                                                                                    NeMo Guardrails
                                                                                    (Injection/Jailbreak)
                                                                                            |
                                                                                            v
                                                                                    Answer + Cited Sources
                                                                                            |
                                                                                    +-------+-------+
                                                                                    |               |
                                                                              React           PdfViewer
                                                                              Frontend        (in-app)
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
│   │   ├── auth_routes.py       # POST /auth/signup, /login, /logout, /me
│   │   ├── chat_routes.py       # CRUD for /chats
│   │   ├── document_routes.py   # Upload/list/delete documents + PDF serving
│   │   └── message_routes.py    # Send message + get chat history
│   └── services/
│       ├── __init__.py
│       ├── llm.py               # LLM provider (Ollama / Gemini / HuggingFace / NVIDIA)
│       ├── embeddings.py        # Qwen3-Embedding-8B (4096-dim) via HuggingFace API
│       ├── vectorstore.py       # ChromaDB integration with embedding function
│       ├── ingestion.py         # PDF + DOCX + Images → chunk → embed → store
│       ├── retriever.py         # Hybrid: BM25 + Vector + Multi-Query + RRF + CrossEncoder
│       ├── query_engine.py      # RAG: retrieve → rerank → filter sources → LLM → answer
│       ├── guardrails.py        # Input/Output guardrails + NeMo Guardrails integration
│       ├── ocr_fallback.py      # Tesseract OCR for scanned PDF pages
│       ├── api_key_manager.py   # Load-balanced API key rotation
│       ├── auth_service.py      # Supabase auth (email/password + Google OAuth)
│       ├── session_service.py   # Chat session CRUD
│       ├── document_service.py  # Upload to Supabase Storage, status tracking
│       ├── message_service.py   # Chat history, conversation context
│       └── upload_utils.py      # Filename sanitization, file size validation
├── config/
│   ├── config.yml               # NeMo Guardrails config (NIM model settings)
│   └── rails.co                 # NeMo Colang rules (mortgage domain enforcement)
├── frontend/                    # React app (Vite + Tailwind + Framer Motion)
│   ├── package.json
│   ├── vite.config.js           # Proxy to backend:8000
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Routes: Home, Login, Signup, Dashboard
│       ├── App.css              # Design system (glassmorphism, gradients, animations)
│       ├── api.js               # API client (auth, chats, docs, messages, PDF URL)
│       ├── context/
│       │   └── AuthContext.jsx   # Auth state (token, user)
│       ├── pages/
│       │   ├── Home.jsx         # Landing page with animated features
│       │   ├── Login.jsx        # Login form with icons
│       │   ├── Signup.jsx       # Signup form with icons
│       │   └── Dashboard.jsx    # Main app (chats + chat view + PDF viewer)
│       └── components/
│           ├── ChatList.jsx     # Sidebar with chat sessions
│           ├── ChatView.jsx     # Chat messages + source citations
│           ├── Chatbox.jsx      # Chat input box
│           ├── FileUpload.jsx   # Drag-and-drop upload zone
│           ├── PdfViewer.jsx    # In-app PDF viewer (react-pdf)
│           ├── Navbar.jsx       # Navigation bar
│           ├── Sidebar.jsx      # Side panel
│           ├── FeatureCard.jsx  # Feature cards (animated)
│           └── TeamCard.jsx     # Team member cards
├── sql/
│   └── schema.sql               # Supabase schema (profiles, sessions, documents, messages + RLS)
├── tests/
│   ├── backend/
│   │   └── test_retriever.py    # Chunk dedup tests
│   └── evaluation/
│       ├── documents/           # Mortgage PDFs for evaluation
│       ├── golden_datasets/     # Golden dataset JSONs (275 questions)
│       ├── evaluate.py          # RAGAS evaluation script
│       └── test_answer_relevancy.py  # Quick metric verification
├── data/
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
# Or use load-balanced keys:
# NVIDIA_API_KEYS=key1,key2,key3

# Embeddings (required)
HUGGINGFACEHUB_API_TOKEN=your_hf_token
# Or load-balanced:
# HF_API_KEYS=key1,key2,key3

# Supabase (required for auth + chat sessions)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=documents

# Guardrails
INPUT_GUARDRAILS_ENABLED=true
OUTPUT_GUARDRAILS_ENABLED=true
NEMO_GUARDRAILS_ENABLED=true

# Upload Security
MAX_UPLOAD_BYTES=26214400
ALLOW_RESET_COLLECTION=false

# Retriever
RETRIEVER_TOP_K=10
MULTI_QUERY_ENABLED=true
MULTI_QUERY_N=3

# OCR (for scanned PDFs)
OCR_FALLBACK_ENABLED=true
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 3. Setup Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run `sql/schema.sql` in the SQL Editor
3. Create a storage bucket named `documents`
4. Copy your project URL and keys to `.env`

### 4. Start Backend

```bash
uvicorn backend.main:app --reload --port 8000
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

### Supported File Types

| Type | Extension | Method |
|------|-----------|--------|
| PDF | `.pdf` | PyMuPDF + OCR fallback |
| Word | `.docx` | python-docx |
| Image | `.jpg`, `.jpeg`, `.png` | Tesseract OCR |

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

### Retriever Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MULTI_QUERY_ENABLED` | `true` | Generate N reformulated queries for better recall |
| `MULTI_QUERY_N` | `3` | Number of reformulated queries per question |
| `RETRIEVER_TOP_K` | `10` | Number of chunks retrieved and sent to LLM |

### Guardrails

| Variable | Default | Description |
|----------|---------|-------------|
| `INPUT_GUARDRAILS_ENABLED` | `true` | Regex-based input safety (injection, jailbreak, harmful) |
| `OUTPUT_GUARDRAILS_ENABLED` | `true` | Regex-based output filtering (length, prompt leakage) |
| `NEMO_GUARDRAILS_ENABLED` | `true` | NeMo input safety (injection, jailbreak via LLM) |
| `MAX_UPLOAD_BYTES` | `26214400` | Max upload size (25MB default) |
| `ALLOW_RESET_COLLECTION` | `false` | Require auth + env flag for `/reset-collection` |

---

## API Endpoints

### Auth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account (email + password) |
| `/auth/login` | POST | Login, returns JWT |
| `/auth/logout` | POST | Invalidate session |
| `/auth/me` | GET | Get current user |

### Chats

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats` | GET | List all chat sessions |
| `/chats` | POST | Create new chat session |
| `/chats/{id}` | PATCH | Rename chat |
| `/chats/{id}` | DELETE | Delete chat + all documents + ChromaDB chunks + Storage |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats/{id}/documents` | GET | List documents in chat |
| `/chats/{id}/documents` | POST | Upload PDF/DOCX/Image → ingest → store |
| `/chats/{id}/documents/{doc_id}` | DELETE | Delete document (ChromaDB + Storage) |
| `/chats/{id}/documents/{doc_id}/pdf` | GET | Serve PDF for in-app viewer |

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
| `/reset-collection` | POST | Wipe and recreate ChromaDB collection (requires auth + env flag) |

---

## Frontend Features

- **Auth** — Login/Signup with email
- **Dashboard** — Chat list sidebar + chat view
- **File Upload** — drag-and-drop zone, accepts PDF, DOCX, JPG, JPEG, PNG
- **Chat Interface** — ask questions about uploaded mortgage documents
- **Source Citations** — only sources cited by the LLM are shown
- **PdfViewer** — in-app PDF viewer with page navigation and zoom
- **Source-to-PDF Link** — click a source to open the PDF at that page
- **Chat History** — persistent messages across sessions
- **Auto-scroll** — chat scrolls to latest message
- **Animations** — framer-motion entry animations, hover effects, glassmorphism

## Security Features

- **Filename Sanitization** — prevents path traversal and null byte injection
- **File Size Validation** — configurable max upload size (25MB default)
- **Input Guardrails** — blocks prompt injection, jailbreak, harmful content
- **Output Guardrails** — filters prompt leakage, truncates long responses
- **NeMo Guardrails** — LLM-based injection/jailbreak detection
- **Auth Required** — reset collection requires authentication + env flag
- **No Local Storage** — files processed via tempfile, deleted after ingestion

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
python -m tests.evaluation.evaluate --resume
```

**What it does:**
1. Ingests all docs from `documents/`
2. Loads all Q&A pairs from `golden_datasets/`
3. Runs RAG pipeline on each question
4. Evaluates with RAGAS collections metrics
5. Saves report to `docs/eval_report.md`
6. Supports `--resume` to continue from last checkpoint

**Metrics:**
| Metric | Target | What It Measures |
|--------|--------|------------------|
| Faithfulness | > 0.8 | Answer grounded in retrieved context |
| Answer Relevancy | > 0.75 | Answer addresses the question |
| Context Precision | > 0.7 | Retrieved chunks are relevant |

---

## Important Rules

1. **Never hardcode API keys** — use `.env` or load-balanced keys
2. **Always set chunk_overlap=50** — never 0
3. **Commit daily** — no version control = risk
4. **Test retrieval before building generation**
5. **Target RAGAS faithfulness > 0.8 before Week 3**

---

*AIforAll Global — Mortgage RAG Team — Week 2 — June 2026*
