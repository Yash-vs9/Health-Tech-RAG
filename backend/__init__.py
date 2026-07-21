"""
Mortgage RAG Backend
====================
FastAPI application for mortgage document Q&A with RAG pipeline.

Modules:
    main            - FastAPI app entrypoint, CORS, legacy endpoints, router includes
    schemas         - Pydantic request/response models for legacy /ingest and /query
    logging_config  - Centralized logging (console + file)

Routes:
    auth_routes     - /auth/* (signup, login, logout, me, Google OAuth)
    chat_routes     - /chats/* (CRUD for chat sessions)
    document_routes - /chats/{id}/documents/* (upload, list, delete, serve PDF/image)
    message_routes  - /chats/{id}/messages/* (send question, get history, feedback)

Services:
    llm             - Multi-provider LLM (NVIDIA NIM / Gemini / HuggingFace / Ollama)
    embeddings      - Qwen3-Embedding-8B (4096-dim) via HuggingFace API with key load balancing
    vectorstore     - Qdrant vector store (upsert, query, delete, collection management)
    ingestion       - PDF/DOCX/Image ingestion: parser + vision LLM + OCR fallback + chunk + embed
    retriever       - Hybrid retrieval: BM25 + Vector + Multi-Query + RRF + CrossEncoder rerank
    query_engine    - RAG query pipeline: guardrails -> retrieve -> rerank -> LLM -> answer
    guardrails      - Input/output regex guardrails + NeMo Guardrails integration
    ocr_fallback    - Tesseract OCR for scanned PDF pages
    api_key_manager - Thread-safe API key rotation with cooldown on rate limits
    auth_service    - Supabase auth (email/password + Google OAuth)
    session_service - Chat session CRUD
    document_service - Document metadata CRUD + Supabase Storage
    message_service - Message CRUD + conversation context builder
    upload_utils    - Filename sanitization, file size validation
"""
