# Tejasva Chadha - Multi-Query Retrieval

This slice covers the Tejasva assignment from the Week 2 team distribution:

- MultiQueryRetriever-based question expansion
- merged retrieval results
- source citation payloads for the UI bridge
- React message and citation components

## Files

- `backend/services/query_engine.py` - retrieval expansion and answer assembly
- `backend/main.py` - FastAPI query and health endpoints
- `frontend/src/components/ChatMessage.jsx` - message bubble with sources
- `frontend/src/components/CitationPanel.jsx` - collapsible citation display
- `tests/evaluation/tejasva_golden_set.json` - Tejasva's 5 citation-grounded Q&A pairs

## Expected behavior

1. A single user question is expanded into three query variants.
2. Retrieval results are merged and returned with source metadata.
3. The frontend renders answer text and citations beneath it.

## Golden dataset

The PDF assigns Tejasva a 5-pair citation-grounded golden dataset. Each item should include the question, expected answer, source document, source page, and answerability metadata.
