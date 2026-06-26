# Health Tech RAG Chatbot — Full Pipeline Setup Guide

> GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Architecture Overview

```
User Upload (PDF)
       |
       v
  [POST /ingest]  -->  PDF Loader (PyMuPDF)  -->  Text Splitter  -->  Embeddings (HuggingFace)
                                                                        |
                                                                        v
                                                              ChromaDB Vector Store
                                                                        |
                                                                        v
User Question  -->  [POST /query]  -->  Retriever  -->  LLM (Ollama)  -->  Answer + Sources
                                                                                |
                                                                                v
                                                                        React/Streamlit UI
```

---

## Team Dependency Order

```
Aakanksha (Docs) --> Soojal (Store) --> Yash (Embed) --> Aryan (Retriever)
  --> Tejasva (Multi-query) --> UI Team --> Lakshya (API) --> Nua (Evaluate) --> Prompts Team
```

---

## Directory Structure

```
Health-Tech-RAG/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app — 3 endpoints
│   ├── schemas.py               # Pydantic request/response models
│   ├── requirements.txt         # Backend-specific dependencies
│   └── services/
│       ├── __init__.py
│       ├── vectorstore.py       # ChromaDB integration layer
│       ├── ingestion.py         # PDF → chunk → embed → store
│       └── query_engine.py      # RAG retriever + LLM answer generation
├── tests/
│   └── evaluation/
│       └── golden_set_lakshya.json   # 5 edge case Q&A pairs
├── docs/                        # Evaluation reports, embedding comparisons
├── prompts/                     # System prompts (.txt files)
├── data/
│   ├── uploaded_pdfs/           # Ingested PDFs stored here
│   └── chroma_db/               # Persistent ChromaDB storage
├── requirements.txt             # Root-level dependencies
├── .env.example                 # Environment variable template
├── Week2_Work_Distribution.md   # Team task breakdown
└── README.md                    # This file
```

---

## Prerequisites

- **Python 3.10+**
- **Ollama** installed locally (for LLM inference)
  - Install: https://ollama.ai
  - Pull model: `ollama pull llama3.2`
- **Git**

---

## Quick Start (Project Leader / Lakshya)

### Step 1: Clone and Enter Repo

```bash
git clone https://github.com/<org>/Health-Tech-RAG.git
cd Health-Tech-RAG
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (defaults work out of the box)
```

### Step 5: Start the API Server

```bash
uvicorn backend.main:app --reload --port 8000
```

### Step 6: Verify Everything Works

Open Swagger UI: http://localhost:8000/docs

Test the 3 endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — returns API + ChromaDB status |
| `/ingest` | POST | Upload a PDF → returns `doc_id`, chunk count |
| `/query` | POST | Ask a question → returns answer + source chunks |

---

## API Endpoints — Detailed

### `GET /health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "chromadb": "connected (150 docs)"
}
```

### `POST /ingest`

**Request:** multipart/form-data with a PDF file

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
  "answer": "Common symptoms include increased thirst, frequent urination, and unexplained weight loss.",
  "sources": [
    {
      "content": "Diabetes mellitus is characterized by...",
      "metadata": {
        "source": "who_guidelines.pdf",
        "page": 12,
        "doc_id": "a1b2c3d4e5f6"
      }
    }
  ]
}
```

---

## Pipeline Integration Guide (For Team Members)

### Soojal — ChromaDB Store

- Collection is auto-created on first access
- Location: `data/chroma_db/` (persistent)
- Distance metric: cosine similarity
- The vectorstore service in `backend/services/vectorstore.py` wraps all ChromaDB operations

### Yash — PDF Ingestion + Embeddings

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (configurable via `.env`)
- **CRITICAL:** Never mix embedding models — use the same model for indexing AND querying
- Text splitting: `chunk_size=512`, `chunk_overlap=50` (never set overlap to 0)
- Ingestion service: `backend/services/ingestion.py`

### Aryan — Retriever + QA Chain

- Retriever config: `k=5`, `score_threshold=0.7`
- Memory: `ConversationBufferMemory` for multi-turn conversation
- Source documents enabled: `return_source_documents=True`
- Query engine: `backend/services/query_engine.py`

### Tejasva — Multi-Query Retrieval

- Use `MultiQueryRetriever` from LangChain
- Generate 3 query variants per user question
- Merge results for better recall
- Bridge output to React components via the `/query` endpoint

### UI Team — React/Streamlit Frontend

- Connect to FastAPI backend via `http://localhost:8000`
- Upload endpoint: `POST /ingest` (multipart/form-data)
- Query endpoint: `POST /query` (JSON)
- Health check: `GET /health`
- Handle loading states and error responses

### Nua — RAGAS Evaluation

- Golden dataset: `tests/evaluation/golden_set_lakshya.json` (Lakshya's 5 edge case pairs)
- Merge all 10 members' Q&A pairs into `tests/evaluation/golden_set.json`
- Metrics: faithfulness (>0.8), answer_relevancy (>0.75), context_precision (>0.7)
- Save results to `docs/eval_report.md`

---

## Golden Dataset Format (For All Members)

Submit exactly **5 Q&A pairs** in this format:

```json
{
  "question_id": "Q001",
  "question": "What are symptoms of Type 2 diabetes?",
  "expected_answer": "Common symptoms include...",
  "source_doc": "who_health_guidelines.pdf",
  "source_page": 12,
  "question_type": "factual",
  "answerability": "TRUE",
  "hallucination_risk": "LOW"
}
```

**Question Types by Member:**

| Member | Type | Label |
|--------|------|-------|
| Aryan | Multi-hop Reasoning | `question_type=multi_hop` |
| Tejasva | Citation-Grounded | `answerability=TRUE`, source mandatory |
| Yash | Query Variations | `question_type=variation` |
| **Lakshya** | **Edge Cases** | **`answerability=FALSE`, `hallucination_risk=HIGH`** |
| Isha | Factual Direct | `question_type=factual` |
| Aakanksha | Factual Direct | `question_type=factual` |
| Soojal | Simple Direct | `question_type=simple` |
| Nua | Simple Direct | `question_type=simple` |

---

## Important Rules

1. **Never mix embedding models** — use the same model for indexing and querying
2. **Always set chunk_overlap=50** — never 0, it kills cross-boundary context
3. **Never hardcode API keys** — use `.env` files with `python-dotenv`
4. **Commit code daily** — no version control = risk
5. **Test retrieval quality BEFORE building generation on top**
6. **Target RAGAS faithfulness > 0.8 before Week 3**

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'backend'` | Run `uvicorn` from the project root |
| ChromaDB connection error | Check `CHROMA_DB_PATH` in `.env`, ensure directory exists |
| Ollama not responding | Run `ollama serve` in a separate terminal |
| Slow first query | First run downloads the embedding model (~80MB), be patient |
| PDF upload fails | Ensure file is valid PDF, check `data/uploaded_pdfs/` permissions |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| RAG Framework | LangChain |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| LLM | Ollama (llama3.2) |
| PDF Loader | PyMuPDF |
| Evaluation | RAGAS |
| Frontend | React / Streamlit |

---

## Week 2 Targets

- [ ] All 3 API endpoints functional and tested via Swagger
- [ ] PDF ingestion pipeline working end-to-end
- [ ] RAG query returning answers with source citations
- [ ] 50 golden Q&A pairs collected (5 per member)
- [ ] RAGAS faithfulness > 0.8, answer_relevancy > 0.75, context_precision > 0.7
- [ ] All code committed to GitHub daily

---

*AIforAll Global — Health Tech Team — Week 2 — June 2026*
