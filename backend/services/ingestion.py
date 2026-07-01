import os
import uuid
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from backend.logging_config import get_logger
from .embeddings import get_embeddings
from . import vectorstore

logger = get_logger("backend.ingestion")


def _load_pdf(file_path: str) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader
    logger.debug("Loading PDF: %s", file_path)
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()
    logger.debug("PDF loaded — pages=%d", len(docs))
    return docs


def _load_docx(file_path: str) -> list[Document]:
    import docx
    logger.debug("Loading DOCX: %s", file_path)
    doc = docx.Document(file_path)
    full_text = "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
    logger.debug("DOCX loaded — paragraphs=%d, chars=%d", len(doc.paragraphs), len(full_text))
    return [Document(page_content=full_text, metadata={"source": os.path.basename(file_path)})]


def ingest_document(file_bytes: bytes, filename: str, doc_id: str | None = None) -> dict:
    if doc_id is None:
        doc_id = str(uuid.uuid4())[:12]
    ext = os.path.splitext(filename)[1].lower()
    logger.info("Starting ingestion — file=%s, ext=%s, doc_id=%s", filename, ext, doc_id)

    upload_dir = os.getenv("UPLOAD_DIR", "./data/uploaded_pdfs")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc_id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    logger.debug("File saved — path=%s, bytes=%d", file_path, len(file_bytes))

    # Load document
    load_start = time.time()
    if ext == ".pdf":
        docs = _load_pdf(file_path)
    elif ext == ".docx":
        docs = _load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    load_elapsed = time.time() - load_start
    logger.info("Document loaded — pages=%d, elapsed=%.2fs", len(docs), load_elapsed)

    # Split into chunks
    chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "],
    )
    split_start = time.time()
    chunks = splitter.split_documents(docs)
    split_elapsed = time.time() - split_start
    logger.info(
        "Split into chunks — count=%d, chunk_size=%d, overlap=%d, elapsed=%.2fs",
        len(chunks), chunk_size, chunk_overlap, split_elapsed,
    )

    # Build embeddings + store
    embeddings = get_embeddings()

    documents = []
    metadatas = []
    ids = []
    for i, chunk in enumerate(chunks):
        documents.append(chunk.page_content)
        meta = chunk.metadata.copy()
        meta["doc_id"] = doc_id
        meta["filename"] = filename
        metadatas.append(meta)
        ids.append(f"{doc_id}_chunk_{i}")

    store_start = time.time()
    vectorstore.add_documents(documents=documents, metadatas=metadatas, ids=ids)
    store_elapsed = time.time() - store_start
    logger.info(
        "Stored in ChromaDB — chunks=%d, elapsed=%.2fs, total_chunks=%d",
        len(chunks), store_elapsed, vectorstore.get_doc_count(),
    )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "num_chunks": len(chunks),
        "status": "success",
    }
