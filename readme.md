# Health Tech RAG Chatbot

> GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## About This Branch

This is the **main** branch — the integration branch where all feature branches are merged to form the **working end-to-end pipeline**.

Each team member works on their own feature branch. Once complete, branches are merged into `main` to build the full system.

### Active Feature Branches

| Branch | Owner | Task | Status |
|--------|-------|------|--------|
| `feat/lakshya-fastapi` | Lakshya | FastAPI Backend (3 endpoints) | In Progress |
| `feat/aryan-retriever` | Aryan | LangChain Retriever + ChromaDB Config | In Progress |
| `feat/yash-ingestion` | Yash | PDF Ingestion Pipeline | In Progress |

### How Merging Works

```
feat/yash-ingestion (PDF Load + Chunk + Embed)
         |
         v
feat/aryan-retriever (Retriever + QA Chain)
         |
         v
feat/lakshya-fastapi (FastAPI Endpoints)
         |
         v
      main  <-- All branches merge here to create the working pipeline
```

**Merge Order (respects team dependency):**
1. `feat/yash-ingestion` — PDF ingestion pipeline (no upstream deps)
2. `feat/aryan-retriever` — Retriever config (depends on ingestion)
3. `feat/lakshya-fastapi` — API layer (depends on retriever + ingestion)

After all merges, `main` contains the complete, runnable system.

---

## Full Pipeline Architecture

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

## Quick Start (After All Merges)

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

# Run
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

## Directory Structure

```
Health-Tech-RAG/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── schemas.py               # Pydantic models
│   └── services/
│       ├── vectorstore.py       # ChromaDB integration
│       ├── ingestion.py         # PDF → chunk → embed → store
│       └── query_engine.py      # Retriever + LLM
├── tests/evaluation/            # Golden dataset Q&A pairs
├── docs/                        # Reports, comparisons
├── prompts/                     # System prompts
├── data/
│   ├── uploaded_pdfs/
│   └── chroma_db/
├── requirements.txt
├── .env.example
└── README.md                    # This file
```

---

## Team Branch Workflow

### For Each Team Member:

1. **Pull latest main** before starting work
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create your feature branch** from main
   ```bash
   git checkout -b feat/<your-name>-<task>
   ```

3. **Work on your branch** — commit regularly

4. **Push your branch**
   ```bash
   git push origin feat/<your-name>-<task>
   ```

5. **Create PR** → merge into `main` after review

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

## Important Rules

1. **Never mix embedding models** — same model for indexing AND querying
2. **Always set chunk_overlap=50** — never 0
3. **Never hardcode API keys** — use `.env`
4. **Commit daily** — no version control = risk
5. **Test retrieval before building generation**
6. **Target RAGAS faithfulness > 0.8 before Week 3**

---

*AIforAll Global — Health Tech Team — Week 2 — June 2026*
