from dotenv import load_dotenv
load_dotenv()

import os
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.logging_config import setup_logging, get_logger
from backend.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SourceChunk,
)
from backend.services import ingestion, query_engine, vectorstore
from backend.routes import auth_routes, chat_routes, document_routes, message_routes

setup_logging()
logger = get_logger("backend.main")

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

app = FastAPI(
    title="Mortgage RAG API",
    description="RAG system for mortgage document Q&A with auth, sessions, and chat history",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── RAG endpoints (existing) ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    logger.info("Health check requested")
    try:
        count = vectorstore.get_doc_count()
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        embed_provider = os.getenv("EMBEDDING_PROVIDER", "local")
        logger.info(
            "Health OK — chunks=%d, llm=%s, embeddings=%s",
            count, llm_provider, embed_provider,
        )
        return HealthResponse(
            status="ok",
            version="1.0.0",
            chromadb=f"connected ({count} chunks)",
            llm=llm_provider,
            embeddings=embed_provider,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return HealthResponse(
            status="degraded",
            version="1.0.0",
            chromadb=f"error: {str(e)}",
            llm="unknown",
            embeddings="unknown",
        )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Ingest rejected — unsupported file type: %s", ext)
        raise HTTPException(status_code=400, detail=f"Only PDF and DOCX files are accepted. Got: {ext}")

    logger.info("Ingest request — file=%s, size=%s", file.filename, file.size)
    start = time.time()
    try:
        file_bytes = await file.read()
        result = ingestion.ingest_document(file_bytes=file_bytes, filename=file.filename)
        elapsed = time.time() - start
        logger.info(
            "Ingest OK — doc_id=%s, chunks=%d, elapsed=%.1fs",
            result["doc_id"], result["num_chunks"], elapsed,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.error("Ingest failed — file=%s, error=%s", file.filename, e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    logger.info("Query request — q=%s, doc_ids=%s", request.question[:80], request.doc_ids)
    start = time.time()
    try:
        result = query_engine.query_rag(
            question=request.question,
            doc_ids=request.doc_ids if request.doc_ids else None,
        )
        elapsed = time.time() - start
        sources = [SourceChunk(content=s["content"], metadata=s["metadata"]) for s in result["sources"]]
        logger.info(
            "Query OK — sources=%d, answer_len=%d, elapsed=%.1fs",
            len(result["sources"]), len(result["answer"]), elapsed,
        )
        return QueryResponse(answer=result["answer"], sources=sources)
    except Exception as e:
        logger.error("Query failed — q=%s, error=%s", request.question[:80], e)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/reset-collection")
async def reset_collection():
    """Delete and recreate ChromaDB collection. Use when switching embedding models."""
    try:
        vectorstore.reset_collection()
        return {"status": "ok", "message": "Collection reset. Re-ingest your documents."}
    except Exception as e:
        logger.error("Collection reset failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# ── Auth & Session routes (Aryan's) ──────────────────────────────────────

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(document_routes.router)
app.include_router(message_routes.router)
