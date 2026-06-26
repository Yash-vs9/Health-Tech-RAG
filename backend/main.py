from dotenv import load_dotenv
load_dotenv()

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

app = FastAPI(
    title="Health RAG API",
    description="GenAI-based RAG Chatbot for Health Document Q&A",
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
        return HealthResponse(
            status="ok",
            version="1.0.0",
            chromadb=f"connected ({count} docs)",
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            version="1.0.0",
            chromadb=f"error: {str(e)}",
        )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        file_bytes = await file.read()
        result = ingestion.ingest_pdf(file_bytes=file_bytes, filename=file.filename)
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
