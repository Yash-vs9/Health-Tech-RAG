import os
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .embeddings import get_embeddings
from . import vectorstore


def _load_pdf(file_path: str) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader
    loader = PyMuPDFLoader(file_path)
    return loader.load()


def _load_docx(file_path: str) -> list[Document]:
    import docx
    doc = docx.Document(file_path)
    full_text = "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
    return [Document(page_content=full_text, metadata={"source": os.path.basename(file_path)})]


def ingest_document(file_bytes: bytes, filename: str) -> dict:
    doc_id = str(uuid.uuid4())[:12]
    ext = os.path.splitext(filename)[1].lower()

    upload_dir = os.getenv("UPLOAD_DIR", "./data/uploaded_pdfs")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc_id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    if ext == ".pdf":
        docs = _load_pdf(file_path)
    elif ext == ".docx":
        docs = _load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

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
