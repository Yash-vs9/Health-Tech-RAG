# Health Tech RAG Chatbot

> GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Pipeline Architecture

```
User Upload (PDF / DOCX)
         |
         v
    POST /ingest  -->  Document Loader  -->  Text Splitter (512/50)  -->  Embeddings
                                                                          |
                                                                +---------+---------+
                                                                |                   |
                                                          EMBEDDING_PROVIDER    EMBEDDING_PROVIDER
                                                            = local               = api
                                                      MiniLM-L6-v2          Qwen3-Embedding-8B
                                                                |                   |
                                                                +---------+---------+
                                                                          |
                                                                          v
                                                                ChromaDB Vector Store
                                                                          |
                                                                          v
User Question  -->  POST /query  -->  Retriever (k=5)  -->  LLM  -->  Answer + Sources
                                                                          |
                                                                +---------+---------+
                                                                |                   |
                                                            LLM_PROVIDER        LLM_PROVIDER
                                                              = ollama             = gemini
                                                            llama3.2           gemini-2.5-flash-lite
                                                                |                   |
                                                                +---------+---------+
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
│   ├── main.py                  # FastAPI app — 3 endpoints
│   ├── schemas.py               # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── llm.py               # LLM provider (Ollama / Gemini)
│       ├── embeddings.py        # Embedding provider (local / API)
│       ├── vectorstore.py       # ChromaDB integration
│       ├── ingestion.py         # PDF + DOCX → chunk → embed → store
│       └── query_engine.py      # RAG: retrieve context → LLM → answer
├── frontend/                    # React app (Vite)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Main app — upload + chat
│       ├── App.css
│       ├── api.js               # API client
│       └── components/
│           ├── FileUpload.jsx   # Drag-and-drop upload
│           ├── ChatMessage.jsx  # Chat message bubble
│           └── CitationPanel.jsx # Source citations
├── prompts/
│   ├── health_system_prompt.txt
│   └── ananya_prompt_test.py
├── tests/
│   ├── backend/test_api.py
│   └── evaluation/
├── data/
│   ├── uploaded_pdfs/           # Uploaded documents
│   └── chroma_db/               # Persistent ChromaDB
├── requirements.txt
├── .env.example
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

Minimal local config (no API keys needed):

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Pull Ollama Model

```bash
ollama pull llama3.2
```

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

### Embedding Provider

| `EMBEDDING_PROVIDER` | Model | Requires | Cost |
|----------------------|-------|----------|------|
| `local` | all-MiniLM-L6-v2 | Downloads ~80MB first run | Free |
| `api` | Qwen3-Embedding-8B | `HUGGINGFACEHUB_API_TOKEN` | Free tier |

**Rule:** Never mix embedding models — use the same for indexing AND querying.

---

## API Endpoints

| Endpoint | Method | Accepts | Description |
|----------|--------|---------|-------------|
| `/health` | GET | — | Health check + provider info |
| `/ingest` | POST | `.pdf` or `.docx` | Upload document → chunk → embed → store |
| `/query` | POST | JSON `{question, doc_ids}` | RAG query → answer + sources |

---

## Frontend Features

- **File Upload** — drag-and-drop or click to browse, accepts PDF and DOCX
- **Chat Interface** — ask questions about uploaded documents
- **Citation Panel** — expandable source chunks for each answer
- **Document List** — shows ingested documents with IDs
- **Auto-scroll** — chat scrolls to latest message

---

## Team Contributions

| Member | Branch | What They Built |
|--------|--------|-----------------|
| Lakshya | `feat/lakshya-fastapi` | FastAPI backend, ChromaDB, ingestion, query engine |
| Soojal | `feat/soojal-chromadb` | ChromaDB collection setup |
| Yash | `feat/yash-ingestion` | PDF ingestion pipeline |
| Aryan | `feat/aryan-retriever` | Retriever config, QA chain |
| Tejasva | `feat/tejasva-multiquery` | React components, tests, prompts |
| Isha | `feat/isha-embeddings` | Embedding model testing |
| Ananya | `feat/ananya-system-prompt` | System prompt, Gemini test |

---

## Important Rules

1. **Never mix embedding models** — same model for indexing AND querying
2. **Always set chunk_overlap=50** — never 0
3. **Never hardcode API keys** — use `.env`
4. **Commit daily** — no version control = risk
5. **Test retrieval before building generation**
6. **Target RAGAS faithfulness > 0.8 before Week 3**

---

*AIforAll Global — Health Tech Team — Week 2 — June 2026*
