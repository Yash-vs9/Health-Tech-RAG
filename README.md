# Health-Tech-RAG

> Production-grade Retrieval-Augmented Generation system for mortgage document Q&A, summarization, and cross-document comparison.

**AIforAll Global — International AI Internship | Week 2 — June 2026**

---

## Live Deployment

| Layer | Platform | Status |
|-------|----------|--------|
| **Backend** | AWS ECS Fargate + ALB | **Live** |
| **Frontend** | Vercel | **Live** |
| **Vector DB** | Qdrant Cloud | **Managed** |
| **Auth + Storage** | Supabase | **Managed** |

---

## What It Does

Upload mortgage documents — PDFs, Word files, scanned images — and ask natural-language questions. The system retrieves the most relevant passages across all uploaded documents, reranks them, and generates a cited answer using a large language model.

**Target users:** Loan officers, compliance teams, underwriters, and anyone working with high-volume mortgage documentation.

---

## Pipeline Architecture

### Ingestion Pipeline

```
User Upload (PDF / DOCX / JPG / JPEG / PNG)
             |
             v
        POST /chats/{id}/documents
             |
             +---> PDF/DOCX ---> PyMuPDF / python-docx ---+
             |                                              |
             +---> Image ---------> PIL -------------------+
             |                            |                 |
             |                            v                 |
             |                    Vision LLM (chart/        |
             |                    table extraction)         |
             |                            |                 |
             |                    +-------+-------+         |
             |                    |               |         |
             |                    v               v         |
             |              Success           Fallback      |
             |                    |               |         |
             |                    |               v         |
             |                    |         Tesseract OCR   |
             |                    |               |         |
             |                    +-------+-------+         |
             |                            |                 |
             +----------------------------+-----------------+
                                            |
                                            v
                                  Merge Text Sources
                           (parser + vision + OCR output)
                                            |
                                            v
                              Text Splitter (1024 chunk / 50 overlap)
                                            |
                                            v
                                      Text Chunks
                                            |
                              +-------------+-------------+
                              |                           |
                              v                           v
                    Qwen3-Embedding-8B              BM25 Index
                   (4096-dim vectors)            (keyword — raw text)
                              |
                              v
                    Qdrant Cloud (Vector Store)
```

### Query Pipeline

```
    User Question
          |
          v
  Input Guardrails (regex)
   injection / jailbreak / harmful
          |
          v
  NeMo Guardrails (LLM-based)
   injection / jailbreak detection
          |
          v
  Greeting Detection ──────── yes ──> LLM (greeting response) ──> Return
          |
         no
          |
          v
  Multi-Query Expansion (N=3)
   LLM generates reformulated queries
          |
          +-----> Query 1 ──> Vector Search (Qdrant)
          +-----> Query 2 ──> Vector Search (Qdrant)
          +-----> Query 3 ──> Vector Search (Qdrant)
          +-----> Original ─> Vector Search (Qdrant)
          |
          +-----> BM25 Search (keyword, original query only)
          |
          v
  Reciprocal Rank Fusion (RRF, k=60)
   merges all ranked lists into single ranking
          |
          v
  CrossEncoder Reranker (ms-marco-MiniLM-L-6-v2)
   reranks fused results by relevance
          |
          v
  Top-K Selection (RETRIEVER_TOP_K=10)
          |
          v
  Context Building
   adds citation tags: [Source N: filename.pdf, Page X, Section: Y]
          |
          v
  LLM (NVIDIA NIM — meta/llama-3.1-70b-instruct)
   generates answer with mandatory citations
          |
          v
  Output Guardrails (regex)
   filters prompt leakage, truncates long responses
          |
          v
  Citation Filtering (Source Filter)
   parses [Source N] tags from answer
   matches to retrieved chunks by filename + page
   deduplicates by filename + page (keeps highest score)
          |
          v
  Answer + Cited Sources
          |
          v
  React Frontend + PdfViewer
```

---

## Evaluation Results

The pipeline was evaluated against a golden dataset of **40 questions** using [RAGAS](https://docs.ragas.io/) collection metrics.

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **Faithfulness** | 0.811 | > 0.80 | PASS |
| **Answer Relevancy** | 0.759 | > 0.75 | PASS |
| **Context Precision** | 0.735 | > 0.70 | PASS |

**All RAGAS targets met.**

<details>
<summary>Per-Question Results (40 questions)</summary>

| # | Question | Answer (truncated) |
|---|----------|-------------------|
| 1 | What were ABC Bank's total assets in fiscal year 2024? | $4.2 trillion |
| 2 | What was ABC Bank's net interest margin in Q4 2024? | 3.45% |
| 3 | What was the NPL ratio of ABC Bank in 2024? | 1.9% |
| 4 | What dividend per share did ABC Bank declare for FY2024? | $0.85 |
| 5 | What were ABC Bank's total operating expenses in 2024? | $12.3 billion |
| 6 | What was ABC Bank's CET1 ratio at year-end 2024? | 13.2% |
| 7 | In how many countries does ABC Bank operate? | 42 countries |
| 8 | What was ABC Bank's retail banking revenue in 2024? | $18.6 billion |
| 9 | What credit rating did S&P assign to ABC Bank in 2024? | AA- |
| 10 | Why did ABC Bank's ROE improve in 2024? | Cost efficiency programs and higher margins |
| 11 | What factors led to the reduction in ABC Bank's provision for credit losses? | Improved credit quality |
| 12 | What trend can be inferred about customer banking behaviour from 2022 to 2024? | Digital-first shift |
| 13 | What does ABC Bank's $2 billion green bond issuance indicate about its strategic priorities? | ESG commitment |
| 14 | What external factor is implied to have negatively affected ABC Bank's investment banking fees? | Market volatility |
| 15 | What can be inferred about ABC Bank's lending aggressiveness in 2024 relative to 2023? | Moderate increase |
| 16 | What risk area does the $320 million fine exposure highlight for ABC Bank? | Compliance/AML |
| 17 | Did ABC Bank meet the regulatory LCR requirement in 2024? | Yes |
| 18 | What caused the increase in ABC Bank's interest expense in 2024? | Higher central bank rates |
| 19 | By how much did ABC Bank's net profit increase from 2023 to 2024? | $1.6 billion (7.8B → 9.4B) |
| 20 | Which business segment contributed the most revenue in 2024? | Retail Banking |
| 21 | Did the cost-to-income ratio improve or worsen in 2024 compared to 2023? | Improved |
| 22 | How does ABC Bank's capital position compare to XYZ Corp? | Stronger (higher CET1, Tier 1) |
| 23 | Which income stream grew faster — net interest income or non-interest income? | Net interest income |
| 24 | What was ABC Bank's retail banking revenue in 2023, and what share of total 2024 revenue did retail represent? | $16.8B / ~44% |
| 25 | What was ABC Bank's CET1 capital in absolute dollar terms? | Not in documents |
| 26 | Did ABC Bank meet its cost-to-income target in 2024? | Not specified in documents |
| 27 | What was the approximate value of non-performing loans in 2024? | $49.4 billion |
| 28 | What was ABC Bank's dividend payout ratio and EPS in 2024? | 34.0% payout ratio |
| 29 | What was ABC Bank's approximate net profit implied by ROA and total assets? | Calculated from ROA × total assets |
| 30 | What was ABC Bank's loan-to-deposit ratio? | 83.9% |
| 31 | What was the percentage growth in fee income from 2023 to 2024? | ~15.3% |
| 32 | What percentage of total operating expenses did staff costs represent? | 43.9% |
| 33 | What was ABC Bank's P/E multiple in 2024? | 8.3x |
| 34 | What was ABC Bank's Tier 1 capital ratio? | 13.6% |
| 35 | By what amount did wealth management AUM grow in 2024? | $90 billion |
| 36 | What was ABC Bank's share price on January 15, 2024? | Not in documents |
| 37 | Who is ABC Bank's chief technology officer? | Not in documents |
| 38 | What was the provision for credit losses broken down by industry sector? | Not in documents |
| 39 | What was ABC Bank's revenue in 2019? | Not in documents |
| 40 | Which specific renewable energy projects were funded by the green bond? | Renewable energy projects |

</details>

---

## Directory Structure

```
Health-Tech-RAG/
├── backend/
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
│   │   ├── document_routes.py   # Upload/list/delete documents + PDF/image serving
│   │   └── message_routes.py    # Send message + get chat history
│   └── services/
│       ├── llm.py               # LLM provider (NVIDIA NIM / Gemini / HuggingFace / Ollama)
│       ├── embeddings.py        # Qwen3-Embedding-8B (4096-dim) via HuggingFace API
│       ├── vectorstore.py       # Qdrant integration with embedding function
│       ├── ingestion.py         # PDF + DOCX + Images → Vision LLM/OCR → chunk → embed → store
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
│   └── rails.co                 # NeMo Colang rules (mortgage domain + injection detection)
├── frontend/                    # React + Vite + Tailwind + Framer Motion
│   └── src/
│       ├── App.jsx              # Routes: Home, Login, Signup, Dashboard
│       ├── api.js               # API client (auth, chats, docs, messages)
│       ├── context/
│       │   └── AuthContext.jsx   # Auth state (token, user)
│       ├── pages/
│       │   ├── Home.jsx         # Landing page
│       │   ├── Login.jsx        # Login form
│       │   ├── Signup.jsx       # Signup form
│       │   └── Dashboard.jsx    # Main app (chats + chat view + PDF/image viewer)
│       └── components/
│           ├── ChatList.jsx     # Sidebar with chat sessions
│           ├── ChatView.jsx     # Chat messages + source citations
│           ├── Chatbox.jsx      # Chat input box
│           ├── FileUpload.jsx   # Drag-and-drop upload zone
│           ├── PdfViewer.jsx    # In-app viewer for PDFs and images
│           ├── Navbar.jsx       # Navigation bar
│           ├── Sidebar.jsx      # Side panel
│           ├── FeatureCard.jsx  # Feature cards (animated)
│           └── TeamCard.jsx     # Team member cards
├── sql/
│   └── schema.sql               # Supabase schema (profiles, sessions, documents, messages + RLS)
├── tests/
│   ├── backend/
│   │   ├── test_retriever.py    # Chunk dedup tests
│   │   └── test_ocr_fallback.py # OCR fallback tests
│   └── evaluation/
│       ├── documents/           # Mortgage PDFs/images for evaluation
│       ├── golden_datasets/     # Golden dataset JSONs (275 questions)
│       ├── evaluate.py          # RAGAS evaluation script
│       └── test_answer_relevancy.py  # Quick metric verification
├── docs/
│   └── eval_report.md           # Full evaluation report with per-question results
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── logs.bat
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11) |
| **LLM** | NVIDIA NIM — `meta/llama-3.1-70b-instruct` |
| **Vision** | NVIDIA NIM — `llama-3.1-nemotron-nano-vl-8b-v1` |
| **Embeddings** | HuggingFace — `Qwen3-Embedding-8B` (4096-dim) |
| **Vector Store** | Qdrant Cloud |
| **Reranker** | CrossEncoder — `ms-marco-MiniLM-L-6-v2` |
| **Auth + DB** | Supabase (PostgreSQL + Auth + Storage) |
| **Guardrails** | NeMo Guardrails + custom regex layers |
| **OCR** | Tesseract (fallback for scanned documents) |
| **Frontend** | React + Vite + Tailwind CSS + Framer Motion |
| **Backend Hosting** | AWS ECS Fargate + Application Load Balancer |
| **Frontend Hosting** | Vercel |

---

## Key Features

### RAG Pipeline

- **Hybrid Retrieval** — Vector search (Qdrant) + BM25 keyword search fused via Reciprocal Rank Fusion
- **Multi-Query Expansion** — Generates N=3 reformulated queries per user question for broader recall
- **CrossEncoder Reranking** — `ms-marco-MiniLM-L-6-v2` reranks fused results before LLM generation
- **Source Citation Filtering** — Only sources actually cited by the LLM are returned to the user

### Document Ingestion

- **Multi-format Support** — PDF, DOCX, JPG, JPEG, PNG
- **Vision Augmentation** — Vision LLM extracts chart data, tables, and visual content from documents
- **OCR Fallback** — Tesseract handles scanned PDF pages when vision model is unavailable
- **Chunk Merging** — Parser text + vision extraction + OCR output merged under `[Vision Augmentation]` blocks

### Security

- **Input Guardrails** — Regex-based detection of prompt injection, jailbreak, and harmful content
- **Output Guardrails** — Filters prompt leakage and truncates oversized responses
- **NeMo Guardrails** — LLM-based injection/jailbreak detection with 70+ mortgage domain examples
- **Auth Required** — JWT-based authentication for all chat and document endpoints
- **File Validation** — Filename sanitization, path traversal prevention, configurable size limits (25MB default)
- **No Local Storage** — Files processed via tempfile, deleted after ingestion

### Frontend

- **Auth** — Email/password + Google OAuth
- **Dashboard** — Chat list sidebar + chat view with persistent history
- **File Upload** — Drag-and-drop zone for PDF, DOCX, JPG, PNG
- **PdfViewer** — In-app PDF viewer with page navigation, zoom, and source-to-PDF linking
- **Source Citations** — Click a cited source to open the PDF/image at that exact location
- **Animations** — Framer Motion entry animations, hover effects, glassmorphism design system

---

## API Endpoints

### Auth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account (email + password) |
| `/auth/login` | POST | Login, returns JWT |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/google/url` | GET | Get Google OAuth URL |
| `/auth/logout` | POST | Invalidate session |
| `/auth/me` | GET | Get current user |

### Chats

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats` | GET | List all chat sessions |
| `/chats` | POST | Create new chat session |
| `/chats/{id}` | PATCH | Rename chat |
| `/chats/{id}` | DELETE | Delete chat + documents + vectors + storage |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats/{id}/documents` | GET | List documents in chat |
| `/chats/{id}/documents` | POST | Upload PDF/DOCX/Image → ingest → store |
| `/chats/{id}/documents/{doc_id}` | DELETE | Delete document (Qdrant + Storage) |
| `/chats/{id}/documents/{doc_id}/pdf` | GET | Serve file for in-app viewer |

### Messages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chats/{id}/messages` | POST | Send question → RAG answer |
| `/chats/{id}/messages` | GET | Get chat history |
| `/messages/{id}/feedback` | PATCH | Up/down vote on answer |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + provider info |

---

## Configuration

All configuration is via environment variables. See `.env.example` for the complete reference.

### LLM Providers

| Provider | Model | Requires |
|----------|-------|----------|
| `nvidia` (default) | `meta/llama-3.1-70b-instruct` | `NVIDIA_API_KEY` or `NVIDIA_API_KEYS` |
| `gemini` | `gemini-2.5-flash-lite` | `GOOGLE_API_KEY` |
| `hf` | `Qwen/Qwen2.5-7B-Instruct` | `HUGGINGFACEHUB_API_TOKEN` |
| `ollama` | `llama3.2` | Local Ollama installation |

### Supported File Types

| Type | Extensions | Method |
|------|-----------|--------|
| PDF | `.pdf` | PyMuPDF + OCR fallback + vision merge |
| Word | `.docx` | python-docx + vision merge (embedded images) |
| Image | `.jpg`, `.jpeg`, `.png` | Vision LLM (chart extraction) + OCR fallback |

### Key Environment Variables

```env
# LLM
LLM_PROVIDER=nvidia
NVIDIA_API_KEYS=key1,key2,key3       # Comma-separated for load balancing
NVIDIA_MODEL=meta/llama-3.1-70b-instruct

# Embeddings
HF_API_KEYS=token1,token2,token3    # Load-balanced HuggingFace tokens

# Vector Store
QDRANT_URL=https://xxx.cloud.qdrant.io
QDRANT_COLLECTION=mortgage_docs

# Auth + Storage
SUPABASE_URL=https://xxx.supabase.co

# Guardrails
INPUT_GUARDRAILS_ENABLED=true
OUTPUT_GUARDRAILS_ENABLED=true
NEMO_GUARDRAILS_ENABLED=true

# Chunking
CHUNK_SIZE=1024
CHUNK_OVERLAP=50

# Retriever
RETRIEVER_TOP_K=10
MULTI_QUERY_ENABLED=true
MULTI_QUERY_N=3
RERANK_ENABLED=true
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for Qdrant)
- Tesseract OCR (for scanned PDF support)

### Backend

```bash
git clone https://github.com/lakshya-varshney/Health-Tech-RAG.git
cd Health-Tech-RAG
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # Fill in your API keys
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Deployment

### Backend (AWS ECS Fargate)

The backend is deployed on **AWS ECS Fargate** behind an Application Load Balancer.

```
Internet → ALB (HTTPS:443) → ECS Fargate (Backend, 1024 CPU / 2GB RAM)
                                    ├── Qdrant Cloud
                                    ├── Supabase
                                    └── NVIDIA NIM API
```

**Architecture:**
- ECS Fargate tasks with autoscaling (2–4 tasks based on CPU)
- ALB with path-based routing (`/auth/*`, `/chats/*`, `/health` → backend)
- Secrets managed via AWS Secrets Manager
- Logs via CloudWatch

### Frontend (Vercel)

The frontend is deployed on **Vercel** with automatic deployments from the main branch.

---

## Use Cases

- **Loan Officers** — Quick lookup of loan terms, rates, and conditions across documents
- **Compliance Teams** — Verify RESPA disclosures, check regulatory adherence
- **Cross-Document Comparison** — Compare terms across multiple loan agreements
- **Summarization** — Get concise summaries of lengthy appraisal reports
- **Chart Analysis** — Extract and query data from financial charts and graphs

---

## Testing

```bash
# Backend tests
pytest tests/backend/

# RAGAS evaluation
python -m tests.evaluation.evaluate --resume
```

Evaluation results are saved to `docs/eval_report.md`.

---

## License

This project was developed as part of the **AIforAll Global — International AI Internship** program.

---

*AIforAll Global — Mortgage RAG Team — Week 2 — June 2026*
