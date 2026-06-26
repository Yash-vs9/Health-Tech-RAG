from pydantic import BaseModel, Field
from typing import List


class IngestResponse(BaseModel):
    doc_id: str = Field(..., description="Unique document ID after ingestion")
    filename: str = Field(..., description="Original filename")
    num_chunks: int = Field(..., description="Number of chunks created from the document")
    status: str = Field(default="success", description="Ingestion status")


class SourceChunk(BaseModel):
    content: str = Field(..., description="Chunk text content")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata (source, page, section)")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question about mortgage documents")
    doc_ids: List[str] = Field(
        default_factory=list,
        description="List of doc_ids to search. Empty list = search all documents."
    )


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Generated answer from RAG pipeline")
    sources: List[SourceChunk] = Field(default_factory=list, description="Source chunks used to generate answer")


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="API health status")
    version: str = Field(default="1.0.0", description="API version")
    chromadb: str = Field(default="connected", description="ChromaDB connection status")
    llm: str = Field(default="ollama", description="LLM provider")
    embeddings: str = Field(default="local", description="Embedding provider")
