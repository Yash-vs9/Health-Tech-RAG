# Ingestion Pipeline Enhancements

## Overview

This update extends the ingestion pipeline to improve document processing for mortgage documents.

## Features

- Added PDF table extraction using `pdfplumber`.
- Added DOCX parsing using `python-docx`.
- Extracts both text and tables from DOCX documents.
- Merges extracted tables with text before chunking.
- Increased chunk size from **512** to **1024** with **100** characters overlap.
- Preserves metadata such as:
  - source
  - page (PDF)
  - content_type (text/table)
  - file_type (pdf/docx)

## Dependencies

```
pdfplumber
python-docx
```

## Supported Formats

- PDF
- DOCX

## Workflow

1. Load document.
2. Extract text.
3. Extract tables.
4. Combine text and table documents.
5. Split into chunks.
6. Generate embeddings.
7. Store embeddings in ChromaDB.

## Validation

The implementation was validated by:

- Successfully extracting tables from PDF documents.
- Successfully extracting text and tables from DOCX documents.
- Generating chunks for both document types before embedding.