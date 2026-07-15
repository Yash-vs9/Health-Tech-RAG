r"""
OCR fallback for scanned PDF pages — plugs into backend/services/ingestion.py

Why: mortgage docs (appraisals, closing disclosures, old faxed agreements)
are frequently scanned images with no text layer. PyMuPDFLoader returns
empty/near-empty page_content for those pages, so they silently never
get embedded/retrieved.

Fix: after PyMuPDFLoader loads pages, check each Document's page_content
length. Any page below a threshold is treated as "likely scanned" — we
re-render that exact page as an image using fitz (already a dependency
here, via _extract_tables_from_pdf) and OCR it with Tesseract. No
pdf2image/Poppler needed, since fitz does the rasterization itself.

Env vars (add to .env / .env.example):
    OCR_FALLBACK_ENABLED=true
    OCR_MIN_CHARS_PER_PAGE=40      # below this, page is considered scanned
    OCR_LANGUAGE=eng
    OCR_ZOOM=2.0                   # 2.0 ~ 144 DPI, higher = sharper but slower
    TESSERACT_CMD=                 # Windows only, e.g.
                                    # C:\Program Files\Tesseract-OCR\tesseract.exe

System dependency (not pip-installable):
    Tesseract OCR binary — Windows: https://github.com/UB-Mannheim/tesseract/wiki
    Linux (Docker/CI):  apt-get install -y tesseract-ocr
    macOS:               brew install tesseract
    (No Poppler needed — fitz/PyMuPDF handles rendering.)

Python dependencies (add to requirements.txt):
    pytesseract
    Pillow
    # PyMuPDF (fitz) already required by ingestion.py — no new dep there
"""

from __future__ import annotations

import os
import io

import fitz
import pytesseract
from PIL import Image
from langchain_core.documents import Document

from backend.logging_config import get_logger

logger = get_logger("backend.ocr_fallback")

# Config
OCR_FALLBACK_ENABLED = os.getenv("OCR_FALLBACK_ENABLED", "true").lower() == "true"
OCR_MIN_CHARS_PER_PAGE = int(os.getenv("OCR_MIN_CHARS_PER_PAGE", "40"))
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
OCR_ZOOM = float(os.getenv("OCR_ZOOM", "2.0"))

_TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD


class OCRFallbackError(Exception):
    """Raised when OCR fallback itself fails (missing binary, corrupt page, etc.)."""


def needs_ocr(page_text: str) -> bool:
    """Heuristic: a page is 'likely scanned' if extracted text is too sparse."""
    return len((page_text or "").strip()) < OCR_MIN_CHARS_PER_PAGE


def _ocr_page_image(file_path: str, page_index: int) -> str:
    """Render one PDF page (0-indexed, matches PyMuPDFLoader's metadata['page']) and OCR it."""
    try:
        doc = fitz.open(file_path)
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(OCR_ZOOM, OCR_ZOOM))
        img_bytes = pix.tobytes("png")
        doc.close()
    except Exception as e:
        raise OCRFallbackError(
            f"Failed to render page {page_index} of {file_path} for OCR: {e}"
        ) from e

    try:
        image = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(image, lang=OCR_LANGUAGE).strip()
    except pytesseract.TesseractNotFoundError as e:
        raise OCRFallbackError(
            "Tesseract binary not found. Install it and/or set TESSERACT_CMD "
            "in .env to its full path."
        ) from e
    except Exception as e:
        raise OCRFallbackError(f"Tesseract OCR failed on page {page_index}: {e}") from e

    return text


def apply_ocr_fallback(docs: list[Document], file_path: str) -> list[Document]:
    """
    Given the list[Document] produced by PyMuPDFLoader (one Document per
    page, metadata["page"] = 0-indexed page number), replace any
    sparse/empty page's content with OCR output. Returns a new list,
    same length and order.

    Call this right after `loader.load()` inside `_load_pdf()`.
    Cheap for the common case — only pages that actually need it get OCR'd.
    """
    if not OCR_FALLBACK_ENABLED:
        return docs

    result = []
    ocr_page_count = 0

    for doc in docs:
        if needs_ocr(doc.page_content):
            page_index = doc.metadata.get("page", 0)
            try:
                ocr_text = _ocr_page_image(file_path, page_index)
                if ocr_text:
                    new_meta = dict(doc.metadata)
                    new_meta["ocr_applied"] = True
                    result.append(Document(page_content=ocr_text, metadata=new_meta))
                    ocr_page_count += 1
                    continue
            except OCRFallbackError as e:
                logger.warning(
                    "OCR fallback skipped for page %d of %s: %s",
                    page_index, os.path.basename(file_path), e,
                )
        result.append(doc)

    if ocr_page_count:
        logger.info(
            "OCR fallback recovered text on %d/%d page(s) of %s",
            ocr_page_count, len(docs), os.path.basename(file_path),
        )

    return result