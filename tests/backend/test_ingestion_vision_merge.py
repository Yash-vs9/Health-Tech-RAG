from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from backend.services.ingestion import (
    _merge_extracted_and_vision_text,
    _load_docx,
    _load_pdf,
)


def test_merge_keeps_extracted_when_vision_is_duplicate():
    extracted = "Revenue grew from 10 to 20."
    vision = "Revenue grew from 10 to 20."

    merged = _merge_extracted_and_vision_text(extracted, vision)

    assert merged == extracted


def test_merge_appends_vision_section_when_new_details_exist():
    extracted = "Revenue grew from 10 to 20."
    vision = "Chart shows quarterly trend: Q1=2, Q2=4, Q3=6, Q4=8."

    merged = _merge_extracted_and_vision_text(extracted, vision)

    assert extracted in merged
    assert "[Vision Augmentation]" in merged
    assert vision in merged


@patch("backend.services.ingestion._extract_tables_from_pdf", return_value={})
@patch("backend.services.ingestion._extract_vision_text_from_pdf", return_value={0: "Extra chart details"})
@patch("backend.services.ingestion.apply_ocr_fallback")
@patch("langchain_community.document_loaders.PyMuPDFLoader")
def test_load_pdf_merges_parser_text_and_vision(
    mock_loader_cls,
    mock_apply_ocr,
    _mock_extract_vision,
    _mock_extract_tables,
):
    base_docs = [Document(page_content="Base parser text", metadata={"page": 0})]

    mock_loader = MagicMock()
    mock_loader.load.return_value = base_docs
    mock_loader_cls.return_value = mock_loader
    mock_apply_ocr.side_effect = lambda docs, _file_path: docs

    docs = _load_pdf("dummy.pdf")

    assert len(docs) == 1
    assert "Base parser text" in docs[0].page_content
    assert "Extra chart details" in docs[0].page_content
    assert docs[0].metadata.get("vision_augmented") is True


@patch("backend.services.ingestion._extract_vision_text_from_docx", return_value=["Image details from vision"])
@patch("docx.Document")
def test_load_docx_merges_paragraphs_and_vision(mock_docx_document, _mock_extract_docx_vision):
    fake_doc = MagicMock()
    fake_doc.paragraphs = [MagicMock(text="Paragraph one."), MagicMock(text="Paragraph two.")]
    mock_docx_document.return_value = fake_doc

    docs = _load_docx("dummy.docx")

    assert len(docs) == 1
    assert "Paragraph one." in docs[0].page_content
    assert "Image details from vision" in docs[0].page_content
    assert docs[0].metadata.get("vision_augmented") is True
