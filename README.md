# Mortgage RAG Chatbot

> RAG system for mortgage document Q&A, summarization, and cross-document comparison
> AIforAll Global — International AI Internship | Week 2 — June 2026

---

## Pipeline Architecture

```
User Upload (PDF / DOCX)
         |
         v
    POST /ingest  -->  Document Loader  -->  Text Splitter (512/50)  -->  Embeddings
                                                                           |
                                                                 Qwen3-Embedding-8B (4096-dim)
                                                                           |
                                                                           v
                                                                 ChromaDB Vector Store
                                                                          |
                                                                          v
User Question  -->  POST /query  -->  Hybrid Retriever  -->  LLM  -->  Answer + Sources
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
                                                              llama3.2   gemini-2.5-flash-lite Qwen2.5-7B  nemotron-3-nano
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
│   ├── main.py                  # FastAPI app — 3 endpoints
│   ├── schemas.py               # Pydantic request/response models
│   ├── logging_config.py        # Centralized logging (console + file)
│   └── services/
│       ├── __init__.py
│       ├── llm.py               # LLM provider (Ollama / Gemini / HuggingFace)
│       ├── embeddings.py        # Embedding provider (local / API)
│       ├── vectorstore.py       # ChromaDB integration
│       ├── ingestion.py         # PDF + DOCX → chunk → embed → store
│       ├── retriever.py         # Hybrid: BM25 + Vector + Multi-Query + RRF
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

Minimal local config (no API keys needed):

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
HUGGINGFACEHUB_API_TOKEN=your_hf_token_here
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
| `hf` | Qwen/Qwen2.5-7B-Instruct | `HUGGINGFACEHUB_API_TOKEN` | Free tier |
| `nvidia` | nemotron-3-nano-omni-30b | `NVIDIA_API_KEY` | Free tier |

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
| `INFO` | Request lifecycle, ingestion progress, LLM provider init, retrieval stats, RAGAS scores |
| `DEBUG` | Chunk RRF scores, BM25/vector hit counts, prompt token count, ChromaDB distances |

### Retriever Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MULTI_QUERY_ENABLED` | `true` | Generate N reformulated queries for better recall |
| `MULTI_QUERY_N` | `3` | Number of reformulated queries per question |

---

## API Endpoints

| Endpoint | Method | Accepts | Description |
|----------|--------|---------|-------------|
| `/health` | GET | — | Health check + provider info |
| `/ingest` | POST | `.pdf` or `.docx` | Upload mortgage doc → chunk → embed → store |
| `/query` | POST | JSON `{question, doc_ids}` | RAG query → answer + sources |

---

## Frontend Features

- **File Upload** — drag-and-drop or click to browse, accepts PDF and DOCX
- **Chat Interface** — ask questions about uploaded mortgage documents
- **Citation Panel** — expandable source chunks for each answer
- **Document List** — shows ingested documents with IDs
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
├── golden_datasets/  ← Golden dataset JSONs from team members
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
