# Integrating OCR Fallback — exact diff for `backend/services/ingestion.py`

You pasted the real file, so this is now exact, not generic.

## 1. Copy the file
Put `ocr_fallback.py` at `backend/services/ocr_fallback.py` (same folder
as `ingestion.py`).

## 2. Add one import at the top of `ingestion.py`

```python
from .ocr_fallback import apply_ocr_fallback
```
(matches the existing relative-import style already used for
`.embeddings` and `. import vectorstore`)

## 3. Edit `_load_pdf()` — one line added

Current:
```python
def _load_pdf(file_path: str) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader
    import fitz

    logger.debug("Loading PDF: %s", file_path)

    tables_by_page = _extract_tables_from_pdf(file_path)

    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    for doc in docs:
        page_idx = doc.metadata.get("page", 0)
        if page_idx in tables_by_page:
            doc.metadata["has_tables"] = True

    logger.debug("PDF loaded — pages=%d, pages_with_tables=%d", len(docs), len(tables_by_page))
    return docs
```

New (only the marked line is added):
```python
def _load_pdf(file_path: str) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader
    import fitz

    logger.debug("Loading PDF: %s", file_path)

    tables_by_page = _extract_tables_from_pdf(file_path)

    loader = PyMuPDFLoader(file_path)
    docs = loader.load()
    docs = apply_ocr_fallback(docs, file_path)     # <-- ADD THIS LINE

    for doc in docs:
        page_idx = doc.metadata.get("page", 0)
        if page_idx in tables_by_page:
            doc.metadata["has_tables"] = True

    logger.debug("PDF loaded — pages=%d, pages_with_tables=%d", len(docs), len(tables_by_page))
    return docs
```

That's it. Runs after page load, before table-flag annotation, so
`has_tables` still applies correctly to OCR'd pages too. Table extraction
itself (`_extract_tables_from_pdf`) is unaffected — tables on scanned
pages won't be caught by `find_tables()` since that needs a real text/line
layer, but that's a separate, harder problem (structured table OCR) —
out of scope for this fallback, which is about not losing page *text*.

## 4. `requirements.txt` — add:
```
pytesseract
Pillow
```
(`PyMuPDF`/`fitz` is already a dependency here — no poppler needed,
unlike a pdf2image-based approach.)

## 5. `.env.example` — add:
```env
# OCR Fallback (for scanned mortgage docs — appraisals, old faxed agreements)
OCR_FALLBACK_ENABLED=true
OCR_MIN_CHARS_PER_PAGE=40
OCR_LANGUAGE=eng
OCR_ZOOM=2.0
TESSERACT_CMD=
```

## 6. Install Tesseract binary (system-level, not pip)
**Windows:** https://github.com/UB-Mannheim/tesseract/wiki — after
installing, set in `.env`:
```
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```
**Linux/Docker:** `apt-get install -y tesseract-ocr`
**macOS:** `brew install tesseract`

## 7. Tests
`tests/test_ocr_fallback.py` mocks `fitz` and `pytesseract` so it runs
without the binary installed. Run:
```bash
pytest tests/test_ocr_fallback.py -v
```
