# Health Tech RAG Chatbot — Full Pipeline Setup Guide

> GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## About This Branch

This is the **main** branch — the integration branch where all feature branches are merged to form the **working end-to-end pipeline**.

---

## Architecture Overview

```
User Upload (PDF)
       |
       v
  POST /ingest  -->  PyMuPDF Loader  -->  Text Splitter (512/50)  -->  Embeddings (MiniLM-L6-v2)
                                                                        |
                                                                        v
                                                              ChromaDB Vector Store
                                                                        |
                                                                        v
User Question  -->  POST /query  -->  Retriever (k=5)  -->  LLM (Ollama)  -->  Answer + Sources
                                                                                    |
                                                                                    v
                                                                            React / Streamlit UI
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
├── ingest.py                    # Yash's standalone ingestion pipeline
├── data.py                      # Soojal's sample test data
├── db_setup.py                  # Soojal's standalone ChromaDB setup
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
└── README.md                    # This file
```

---

## Merged Feature Branches

| Branch | Owner | Task | Merged |
|--------|-------|------|--------|
| `feat/lakshya-fastapi` | Lakshya | FastAPI Backend (3 endpoints) | Yes |
| `feat/soojal-chromadb` | Soojal | ChromaDB Collection Setup | Yes |
| `feat/yash-ingestion` | Yash | PDF Ingestion Pipeline | Yes |
| `feat/aryan-retriever` | Aryan | Retriever + QA Chain | Pending |
| `feat/tejasva-multiquery` | Tejasva | Multi-Query Retrieval | Pending |
| `feat/isha-embeddings` | Isha | Embedding Testing | Pending |
| `feat/ananya-system-prompt` | Ananya | System Prompts | Pending |

---

## Quick Start

```bash
# Clone main
git clone https://github.com/<org>/Health-Tech-RAG.git
cd Health-Tech-RAG

# Setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Pull LLM model
ollama pull llama3.2

# Configure
cp .env.example .env

# Run API server
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** — test all endpoints via Swagger UI.

---

## API Endpoints

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/health` | GET | Health check | — | `status`, `chromadb` connection info |
| `/ingest` | POST | Upload PDF | multipart/form-data | `doc_id`, `filename`, `num_chunks` |
| `/query` | POST | Ask question | `question` + `doc_ids` | `answer` + `sources` |

---

## Ingestion Pipeline (Yash's Contribution)

The standalone ingestion pipeline (`ingest.py`) handles:

1. **PDF Loading** — `PyMuPDFLoader` extracts text + metadata
2. **Chunking** — `RecursiveCharacterTextSplitter` (512 tokens, 50 overlap)
3. **Embedding** — `HuggingFaceEndpointEmbeddings` (Qwen3-Embedding-8B via API)
4. **Storage** — `Chroma.from_documents()` persists to local `chroma_db/`

The FastAPI backend (`backend/services/ingestion.py`) provides the same pipeline integrated into the API via `POST /ingest`.

---

## ChromaDB Setup (Soojal's Contribution)

- Collection: `health_docs`
- Distance: cosine similarity (`hnsw:space = cosine`)
- Standalone setup: `db_setup.py`
- Integrated in backend: `backend/services/vectorstore.py`

---

## Pipeline Integration Guide

### Aryan — Retriever + QA Chain
- Retriever: `k=5`, `score_threshold=0.7`
- Memory: `ConversationBufferMemory`
- Source documents: `return_source_documents=True`
- File: `backend/services/query_engine.py`

### Tejasva — Multi-Query Retrieval
- Use `MultiQueryRetriever` from LangChain
- 3 query variants per question, merge results
- Bridge to React via `/query` endpoint

### Isha — Embedding Testing
- Compare: MiniLM-L6-v2 vs BAAI/bge-large-en-v1.5
- Test chunk sizes: 256 / 512 / 1024
- Document findings in `docs/embedding_comparison.md`

### UI Team — Frontend
- Connect to FastAPI at `http://localhost:8000`
- Upload: `POST /ingest` (multipart/form-data)
- Query: `POST /query` (JSON)
- Health: `GET /health`

### Nua — RAGAS Evaluation
- Merge all Q&A pairs into `tests/evaluation/golden_set.json`
- Metrics: faithfulness (>0.8), answer_relevancy (>0.75), context_precision (>0.7)
- Save to `docs/eval_report.md`

---

## Golden Dataset Format

Submit exactly **5 Q&A pairs** per member:

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

---

## Important Rules

1. **Never mix embedding models** — same model for indexing AND querying
2. **Always set chunk_overlap=50** — never 0
3. **Never hardcode API keys** — use `.env`
4. **Commit daily** — no version control = risk
5. **Test retrieval before building generation**
6. **Target RAGAS faithfulness > 0.8 before Week 3**

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

*AIforAll Global — Health Tech Team — Week 2 — June 2026*
