"""
Tests for OCR fallback — matches backend/services/ingestion.py's real
_load_pdf() output shape: list[langchain_core.documents.Document].

Run: pytest tests/test_ocr_fallback.py -v

These mock fitz + pytesseract so they run without Tesseract installed.
"""

from unittest.mock import patch, MagicMock

from langchain_core.documents import Document

from backend.services.ocr_fallback import (
    needs_ocr,
    apply_ocr_fallback,
    OCR_MIN_CHARS_PER_PAGE,
)


def test_needs_ocr_flags_empty_page():
    assert needs_ocr("") is True
    assert needs_ocr("   ") is True


def test_needs_ocr_flags_sparse_page():
    assert needs_ocr("a" * (OCR_MIN_CHARS_PER_PAGE - 1)) is True


def test_needs_ocr_skips_normal_page():
    assert needs_ocr("This is a normal page with plenty of extracted text. " * 3) is False


@patch("backend.services.ocr_fallback.pytesseract.image_to_string")
@patch("backend.services.ocr_fallback.Image.open")
@patch("backend.services.ocr_fallback.fitz")
def test_fallback_replaces_only_sparse_pages(mock_fitz, mock_image_open, mock_ocr):
    # page 0: normal text -> untouched
    # page 1: empty (scanned) -> OCR'd
    docs = [
        Document(page_content="Normal extractable text, nothing scanned here at all really.", metadata={"page": 0}),
        Document(page_content="", metadata={"page": 1}),
    ]

    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"fake-png-bytes"
    mock_page = MagicMock()
    mock_page.get_pixmap.return_value = mock_pix
    mock_doc = MagicMock()
    mock_doc.__getitem__.return_value = mock_page
    mock_fitz.open.return_value = mock_doc
    mock_fitz.Matrix.return_value = MagicMock()

    mock_ocr.return_value = "Recovered scanned text for page 2"

    result = apply_ocr_fallback(docs, "dummy.pdf")

    assert result[0].page_content == docs[0].page_content   # untouched
    assert result[0].metadata.get("ocr_applied") is None
    assert result[1].page_content == "Recovered scanned text for page 2"
    assert result[1].metadata.get("ocr_applied") is True
    mock_fitz.open.assert_called_once_with("dummy.pdf")


@patch("backend.services.ocr_fallback.fitz")
def test_fallback_does_not_crash_ingestion_on_ocr_failure(mock_fitz):
    mock_fitz.open.side_effect = Exception("corrupt PDF")

    docs = [Document(page_content="", metadata={"page": 0})]
    result = apply_ocr_fallback(docs, "dummy.pdf")

    # Falls back to original (empty) doc rather than raising
    assert result[0].page_content == ""


def test_fallback_disabled_returns_docs_unchanged():
    with patch("backend.services.ocr_fallback.OCR_FALLBACK_ENABLED", False):
        docs = [Document(page_content="", metadata={"page": 0})]
        result = apply_ocr_fallback(docs, "dummy.pdf")
        assert result == docs