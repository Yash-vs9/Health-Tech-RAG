"""
FastAPI application entrypoint.

Sets up the Mortgage RAG API with CORS, health check, legacy ingest/query
endpoints, and mounts the auth/chat/document/message routers.

Startup sequence:
    1. Load .env via python-dotenv
    2. Initialize logging (console + file)
    3. Configure CORS (localhost origins + FRONTEND_URL)
    4. Mount routers: auth, chats, documents, messages

Legacy endpoints (no auth required):
    GET  /health           - Health check + vector count + LLM provider
    POST /ingest           - Upload and ingest a document
    POST /query            - RAG query without chat context
    POST /reset-collection - Wipe Qdrant collection (requires auth + env flag)

Env vars used:
    FRONTEND_URL          - Allowed CORS origin
    LLM_PROVIDER          - Reported in /health response
    ALLOW_RESET_COLLECTION - Must be "true" + auth to use /reset-collection
"""

from dotenv import load_dotenv
load_dotenv()

import os
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.logging_config import setup_logging, get_logger
from backend.services.upload_utils import get_max_upload_bytes, get_upload_file_size, safe_filename
from backend.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SourceChunk,
)
from backend.services import ingestion, query_engine, vectorstore
from backend.services import auth_service
from backend.routes import auth_routes, chat_routes, document_routes, message_routes

setup_logging()
logger = get_logger("backend.main")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".jpg", ".jpeg", ".png"}

app = FastAPI(
    title="Mortgage RAG API",
    description="RAG system for mortgage document Q&A with auth, sessions, and chat history",
    version="1.0.0",
)

frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
allowed_origins = ["http://localhost:3000", "http://localhost:5173"]
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        logger.info(
            "Health OK — chunks=%d, llm=%s, embeddings=Qwen3-Embedding-8B",
            count, llm_provider,
        )
        return HealthResponse(
            status="ok",
            version="1.0.0",
            chromadb=f"connected ({count} chunks)",
            llm=llm_provider,
            embeddings="Qwen3-Embedding-8B",
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
    original_filename = file.filename or ""
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Ingest rejected — unsupported file type: %s", ext)
        raise HTTPException(status_code=400, detail=f"Only PDF, DOCX, JPG, JPEG and PNG files are accepted. Got: {ext}")

    if get_upload_file_size(file) > get_max_upload_bytes():
        raise HTTPException(status_code=413, detail="Uploaded file is too large")

    try:
        safe_filename(original_filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("Ingest request — file=%s, size=%s", original_filename, get_upload_file_size(file))
    start = time.time()
    try:
        file_bytes = await file.read()
        result = ingestion.ingest_document(file_bytes=file_bytes, filename=original_filename)
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
        result = await query_engine.query_rag(
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
async def reset_collection(user: dict = Depends(auth_service.get_current_user)):
    """Delete and recreate Qdrant collection. Use when switching embedding models."""
    if os.getenv("ALLOW_RESET_COLLECTION", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Reset collection is disabled")

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
