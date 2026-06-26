from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SourceChunk,
)
from backend.services import ingestion, query_engine, vectorstore

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

app = FastAPI(
    title="Mortgage RAG API",
    description="RAG system for mortgage document Q&A, summarization, and cross-document comparison",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        count = vectorstore.get_doc_count()
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        embed_provider = os.getenv("EMBEDDING_PROVIDER", "local")
        return HealthResponse(
            status="ok",
            version="1.0.0",
            chromadb=f"connected ({count} chunks)",
            llm=llm_provider,
            embeddings=embed_provider,
        )
    except Exception as e:
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
        raise HTTPException(status_code=400, detail=f"Only PDF and DOCX files are accepted. Got: {ext}")

    try:
        file_bytes = await file.read()
        result = ingestion.ingest_document(file_bytes=file_bytes, filename=file.filename)
        return IngestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = query_engine.query_rag(
            question=request.question,
            doc_ids=request.doc_ids if request.doc_ids else None,
        )
        sources = [SourceChunk(content=s["content"], metadata=s["metadata"]) for s in result["sources"]]
        return QueryResponse(answer=result["answer"], sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
