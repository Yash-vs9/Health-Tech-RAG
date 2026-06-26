# RAG PDF Ingestion Pipeline

A local, Python-based document ingestion pipeline for a Retrieval-Augmented Generation (RAG) system. This script loads PDF documents, splits them into context-aware chunks, generates vector embeddings using a free, local model, and persistently stores them in a Chroma vector database.

## Features

* **PDF Parsing**: Uses `PyMuPDFLoader` for fast and accurate text extraction from PDFs, including built-in document metadata.
* **Smart Chunking**: Utilizes LangChain's `RecursiveCharacterTextSplitter` with overlapping chunks (`chunk_size=512`, `chunk_overlap=50`) to ensure context isn't lost across chunk boundaries.
* **Embeddings**: Generates dense vector embeddings using HuggingFace's `Qwen3-Embedding-8b`.
* **Vector Storage**: Stores embeddings and metadata locally using `ChromaDB` for fast retrieval during the querying phase.

## Prerequisites

* Python 3.9+
* A virtual environment (`.venv`) is recommended.

## Installation

1. Clone or download this repository to your local machine.
2. Open your terminal and activate your virtual environment:
   ```bash
   source .venv/bin/activate  # On Mac/Linux
   # or
   .venv\Scripts\activate     # On Windows