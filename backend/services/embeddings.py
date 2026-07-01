from __future__ import annotations

import os
from backend.logging_config import get_logger

logger = get_logger("backend.embeddings")

_embeddings = None

EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
EMBEDDING_DIM = 4096


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    from langchain_huggingface import HuggingFaceEndpointEmbeddings

    token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        raise ValueError("HUGGINGFACEHUB_API_TOKEN not set. Add your HF token to .env")

    _embeddings = HuggingFaceEndpointEmbeddings(
        model=EMBEDDING_MODEL,
        task="feature-extraction",
        huggingfacehub_api_token=token,
    )
    logger.info("Embeddings ready — model=%s, dim=%d", EMBEDDING_MODEL, EMBEDDING_DIM)
    return _embeddings
