"""Tests for multi-query dedup fix — keeps multiple chunks from same doc."""

from langchain_core.documents import Document
from backend.services.retriever import _chunk_key


def test_chunk_key_unique_per_chunk():
    """Two chunks from same doc with different content get different keys."""
    doc1 = Document(
        page_content="Early diagnosis helps reduce complications.",
        metadata={"doc_id": "guidelines.pdf", "page": 13, "section": "Complications"},
    )
    doc2 = Document(
        page_content="Follow-up care is important after abnormal test results.",
        metadata={"doc_id": "guidelines.pdf", "page": 13, "section": "Complications"},
    )
    key1 = _chunk_key(doc1, doc1.metadata)
    key2 = _chunk_key(doc2, doc2.metadata)
    assert key1 != key2, "Same doc, different content should produce different keys"


def test_chunk_key_same_content_same_key():
    """Same content produces same key."""
    meta = {"doc_id": "guidelines.pdf", "page": 13, "section": "Complications"}
    doc = Document(page_content="Same text here.", metadata=meta)
    key1 = _chunk_key(doc, meta)
    key2 = _chunk_key(doc, meta)
    assert key1 == key2


def test_chunk_key_uses_chunk_id_if_available():
    """When chunk_id is in metadata, use it directly."""
    meta = {"doc_id": "guidelines.pdf", "chunk_id": "abc_123"}
    doc = Document(page_content="Some text", metadata=meta)
    key = _chunk_key(doc, meta)
    assert key == "guidelines.pdf::abc_123"
