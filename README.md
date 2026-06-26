# Health Tech RAG Chatbot

> GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Pipeline Architecture

```
User Upload (PDF)
       |
       v
  POST /ingest  -->  PyMuPDF Loader  -->  Text Splitter (512/50)  -->  Embeddings
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
                                                                  Response to UI
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
│       ├── ingestion.py         # PDF → chunk → embed → store
│       └── query_engine.py      # RAG: retrieve context → LLM answer
├── frontend/src/components/
│   ├── ChatMessage.jsx          # Chat message bubble
│   └── CitationPanel.jsx        # Source citations panel
├── prompts/
│   ├── health_system_prompt.txt # Health domain system prompt
│   └── ananya_prompt_test.py    # Gemini prompt test script
├── tests/
│   ├── backend/test_api.py      # API endpoint tests
│   └── evaluation/
│       ├── golden_set_lakshya.json   # 5 edge case pairs
│       └── tejasva_golden_set.json   # 5 citation-grounded pairs
├── data/
│   ├── uploaded_pdfs/           # Ingested PDFs
│   └── chroma_db/               # Persistent ChromaDB
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone and Setup

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

Edit `.env` — **minimal config for local setup (no API keys needed):**

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

### 4. Run the API

```bash
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** — test via Swagger UI.

---

## Configuration Options

### LLM Provider

| `LLM_PROVIDER` | Model | Requires | Cost |
|----------------|-------|----------|------|
| `ollama` | llama3.2 | Ollama installed locally | Free |
| `gemini` | gemini-2.5-flash-lite | `GOOGLE_API_KEY` | Free tier available |

### Embedding Provider

| `EMBEDDING_PROVIDER` | Model | Requires | Cost |
|----------------------|-------|----------|------|
| `local` | all-MiniLM-L6-v2 | Downloads ~80MB on first run | Free |
| `api` | Qwen3-Embedding-8B | `HUGGINGFACEHUB_API_TOKEN` | Free tier available |

**Rule:** Never mix embedding models — use the same model for indexing AND querying.

---

## API Endpoints

### `GET /health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "chromadb": "connected (47 chunks)",
  "llm": "ollama",
  "embeddings": "local"
}
```

### `POST /ingest`

Upload a PDF → parse → chunk → embed → store.

**Request:** `multipart/form-data` with file field `file`

**Response:**
```json
{
  "doc_id": "a1b2c3d4e5f6",
  "filename": "who_guidelines.pdf",
  "num_chunks": 47,
  "status": "success"
}
```

### `POST /query`

Ask a question → retrieve context → generate answer.

**Request:**
```json
{
  "question": "What are the symptoms of diabetes?",
  "doc_ids": ["a1b2c3d4e5f6"]
}
```

**Response:**
```json
{
  "answer": "Common symptoms include increased thirst, frequent urination...",
  "sources": [
    {
      "content": "Diabetes mellitus is characterized by...",
      "metadata": {"source": "who_guidelines.pdf", "page": 12, "doc_id": "a1b2c3d4e5f6"}
    }
  ]
}
```

---

## Team Contributions

| Member | Branch | What They Built |
|--------|--------|-----------------|
| Lakshya | `feat/lakshya-fastapi` | FastAPI backend, ChromaDB integration, ingestion, query engine |
| Soojal | `feat/soojal-chromadb` | ChromaDB collection setup, sample test data |
| Yash | `feat/yash-ingestion` | PDF ingestion pipeline (PyMuPDF + chunking + embedding) |
| Aryan | `feat/aryan-retriever` | Retriever config (k=5), QA chain, Groq LLM integration |
| Tejasva | `feat/tejasva-multiquery` | React components (ChatMessage, CitationPanel), tests, prompts |
| Isha | `feat/isha-embeddings` | Embedding model testing (Qwen3-Embedding-8B) |
| Ananya | `feat/ananya-system-prompt` | Health system prompt, Gemini prompt test |

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
