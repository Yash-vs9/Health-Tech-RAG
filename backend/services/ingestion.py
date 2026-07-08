import os
import uuid
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from backend.logging_config import get_logger
from .embeddings import get_embeddings
from . import vectorstore
from .ocr_fallback import apply_ocr_fallback

from PIL import Image
import pytesseract

from backend.services.retriever import refresh_bm25


logger = get_logger("backend.ingestion")


# ── Table extraction helpers ─────────────────────────────────────────────


def _table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    """Convert table headers + rows into clean markdown format."""
    # Pad cells to align columns
    all_rows = [headers] + rows
    col_widths = [max(len(str(cell)) for cell in col) for col in zip(*all_rows)] if all_rows else []

    def format_row(cells):
        parts = []
        for cell, w in zip(cells, col_widths):
            parts.append(str(cell).ljust(w))
        return "| " + " | ".join(parts) + " |"

    lines = [format_row(headers)]
    lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
    for row in rows:
        # Pad row if it has fewer columns than headers
        padded = row + [""] * (len(headers) - len(row))
        lines.append(format_row(padded))
    return "\n".join(lines)


def _extract_tables_from_pdf(file_path: str) -> dict[int, list[str]]:
    """
    Extract tables from each page of a PDF using PyMuPDF's find_tables().

    Returns: {page_index: [table_markdown_str, ...]}
    """
    import fitz

    tables_by_page = {}
    doc = fitz.open(file_path)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        tab_finder = page.find_tables()

        if not tab_finder.tables:
            continue

        page_tables = []
        for table in tab_finder.tables:
            try:
                data = table.extract()
                if not data or len(data) < 2:
                    continue

                # First row as headers
                headers = [str(cell).strip() if cell else "" for cell in data[0]]
                rows = []
                for row in data[1:]:
                    rows.append([str(cell).strip() if cell else "" for cell in row])

                # Skip tiny tables (1 row, 1 col — likely noise)
                if len(rows) < 1 or len(headers) < 2:
                    continue

                md = _table_to_markdown(headers, rows)
                page_tables.append(md)
            except Exception as e:
                logger.debug("Table extraction failed on page %d: %s", page_idx, e)
                continue

        if page_tables:
            tables_by_page[page_idx] = page_tables
            logger.debug("Page %d — %d table(s) extracted", page_idx, len(page_tables))

    doc.close()
    logger.info(
        "PDF table extraction done — file=%s, pages_with_tables=%d",
        os.path.basename(file_path), len(tables_by_page),
    )
    return tables_by_page


def _extract_tables_from_docx(file_path: str) -> list[str]:
    """
    Extract all tables from a DOCX file.

    Returns: list of markdown-formatted table strings.
    """
    import docx

    doc = docx.Document(file_path)
    all_tables = []

    for table_idx, table in enumerate(doc.tables):
        try:
            if len(table.rows) < 2 or len(table.columns) < 2:
                continue

            headers = [cell.text.strip() for cell in table.rows[0].cells]
            rows = []
            for row in table.rows[1:]:
                rows.append([cell.text.strip() for cell in row.cells])

            md = _table_to_markdown(headers, rows)
            all_tables.append(md)
            logger.debug("DOCX table %d — %d rows x %d cols", table_idx, len(rows), len(headers))
        except Exception as e:
            logger.debug("DOCX table %d extraction failed: %s", table_idx, e)
            continue

    logger.info("DOCX table extraction — file=%s, tables=%d", os.path.basename(file_path), len(all_tables))
    return all_tables


def _build_table_document(
    table_md: str,
    source: str,
    page_number: int | None = None,
    table_index: int = 0,
    doc_id: str = "",
    filename: str = "",
) -> Document:
    """Create a Document for an extracted table with metadata."""
    meta = {
        "source": source,
        "doc_id": doc_id,
        "filename": filename,
        "is_table": True,
        "table_index": table_index,
    }
    if page_number is not None:
        meta["page_number"] = page_number

    # Prepend a header so the LLM knows this is a table
    content = f"[Table]\n{table_md}\n[/Table]"
    return Document(page_content=content, metadata=meta)


# ── Document loaders ─────────────────────────────────────────────────────


def _load_pdf(file_path: str) -> list[Document]:
    """
    Load PDF pages as Documents, with tables extracted and formatted as
    markdown table chunks (marked with is_table=True metadata).

    Pages with little/no extractable text (scanned/faxed pages, common in
    older mortgage documents) are OCR'd via Tesseract as a fallback so
    they don't silently disappear from retrieval.
    """
    from langchain_community.document_loaders import PyMuPDFLoader
    import fitz

    logger.debug("Loading PDF: %s", file_path)

    # Extract tables first
    tables_by_page = _extract_tables_from_pdf(file_path)

    # Load text pages
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    # OCR fallback for scanned/sparse-text pages
    docs = apply_ocr_fallback(docs, file_path)

    # Remove table text from page content to avoid duplication,
    # and attach table metadata
    for doc in docs:
        page_idx = doc.metadata.get("page", 0)
        if page_idx in tables_by_page:
            # Mark that this page has tables (content still kept for context)
            doc.metadata["has_tables"] = True

    logger.debug("PDF loaded — pages=%d, pages_with_tables=%d", len(docs), len(tables_by_page))
    return docs


def _load_docx(file_path: str) -> list[Document]:
    """Load DOCX paragraphs as a Document, tables extracted separately."""
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

    # ── Load document ──────────────────────────────────────────────────
    load_start = time.time()
   
    if ext == ".pdf":
        docs = _load_pdf(file_path)
        table_docs = _extract_tables_as_docs_pdf(file_path, doc_id, filename)

    elif ext == ".docx":
        docs = _load_docx(file_path)
        table_docs = _extract_tables_as_docs_docx(file_path, doc_id, filename)

    elif ext in [".jpg", ".jpeg", ".png"]:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)

        docs = [
            Document(
                page_content=text,
                metadata={"source": filename}
            )
        ]
        table_docs = []

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    load_elapsed = time.time() - load_start
    logger.info(
        "Document loaded — pages=%d, table_chunks=%d, elapsed=%.2fs",
        len(docs), len(table_docs), load_elapsed,
    )

    # ── Split text into chunks (tables are kept separate) ──────────────
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

    # ── Build embeddings + store ───────────────────────────────────────
    embeddings = get_embeddings()

    documents = []
    metadatas = []
    ids = []

    # 1) Text chunks
    total_chunks = len(chunks) + len(table_docs)
    for i, chunk in enumerate(chunks):
        documents.append(chunk.page_content)
        meta = chunk.metadata.copy()

        meta["doc_id"] = doc_id
        meta["filename"] = filename
        meta["chunk_index"] = i
        meta["total_chunks"] = total_chunks
        meta["is_table"] = False

        if "page" in meta and isinstance(meta["page"], int):
            meta["page_number"] = meta["page"] + 1

        first_line = chunk.page_content.split("\n")[0].strip()
        if len(first_line) < 100 and (
            first_line.isupper()
            or first_line.endswith(":")
            or first_line.startswith("#")
            or first_line.startswith("Section")
            or first_line.startswith("Article")
        ):
            meta["section"] = first_line
        elif "section" not in meta:
            meta["section"] = ""

        meta["content_preview"] = chunk.page_content[:150].replace("\n", " ").strip()
        metadatas.append(meta)
        ids.append(f"{doc_id}::chunk_{i}")

    # 2) Table chunks (atomic — not split further)
    for j, tdoc in enumerate(table_docs):
        documents.append(tdoc.page_content)
        meta = tdoc.metadata.copy()
        meta["doc_id"] = doc_id
        meta["filename"] = filename
        meta["chunk_index"] = len(chunks) + j
        meta["total_chunks"] = total_chunks
        meta["is_table"] = True
        meta["content_preview"] = tdoc.page_content[:150].replace("\n", " ").strip()
        metadatas.append(meta)
        ids.append(f"{doc_id}::table_{j}")

    store_start = time.time()
    vectorstore.add_documents(documents=documents, metadatas=metadatas, ids=ids)

    refresh_bm25()

    store_elapsed = time.time() - store_start
    logger.info(
        "Stored in ChromaDB — text_chunks=%d, table_chunks=%d, elapsed=%.2fs, total=%d",
        len(chunks), len(table_docs), store_elapsed, vectorstore.get_doc_count(),
    )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "num_chunks": len(chunks) + len(table_docs),
        "num_tables": len(table_docs),
        "status": "success",
    }


def _extract_tables_as_docs_pdf(file_path: str, doc_id: str, filename: str) -> list[Document]:
    """Extract PDF tables and return them as individual Documents."""
    tables_by_page = _extract_tables_from_pdf(file_path)
    result = []
    for page_idx, page_tables in tables_by_page.items():
        for table_idx, table_md in enumerate(page_tables):
            result.append(_build_table_document(
                table_md=table_md,
                source=file_path,
                page_number=page_idx + 1,
                table_index=table_idx,
                doc_id=doc_id,
                filename=filename,
            ))
    return result


def _extract_tables_as_docs_docx(file_path: str, doc_id: str, filename: str) -> list[Document]:
    """Extract DOCX tables and return them as individual Documents."""
    table_mds = _extract_tables_from_docx(file_path)
    result = []
    for idx, table_md in enumerate(table_mds):
        result.append(_build_table_document(
            table_md=table_md,
            source=file_path,
            table_index=idx,
            doc_id=doc_id,
            filename=filename,
        ))
    return result