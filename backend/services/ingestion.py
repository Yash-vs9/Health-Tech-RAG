import os
import uuid
import tempfile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from . import vectorstore

_model = None


def get_embeddings():
    global _model
    if _model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _model = HuggingFaceEmbeddings(model_name=model_name)
    return _model


def ingest_pdf(file_bytes: bytes, filename: str) -> dict:
    doc_id = str(uuid.uuid4())[:12]

    upload_dir = os.getenv("UPLOAD_DIR", "./data/uploaded_pdfs")
    os.makedirs(upload_dir, exist_ok=True)
    pdf_path = os.path.join(upload_dir, f"{doc_id}_{filename}")
    with open(pdf_path, "wb") as f:
        f.write(file_bytes)

    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)

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

    vectorstore.add_documents(documents=documents, metadatas=metadatas, ids=ids)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "num_chunks": len(chunks),
        "status": "success",
    }
