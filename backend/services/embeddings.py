"""
Load-balanced HuggingFace embeddings — Qwen3-Embedding-8B (4096-dim).

Wraps HuggingFaceEndpointEmbeddings with API key rotation. Each call to
embed_documents or embed_query gets a fresh key from the key manager.
On rate limit (429/402), retries with the next key up to MAX_RETRIES.

Classes:
    LoadBalancedEmbeddings(Embeddings)
        embed_documents(texts) -> list[list[float]]
        embed_query(text) -> list[float]

Functions:
    get_embeddings() -> LoadBalancedEmbeddings  (singleton)

Constants:
    EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
    EMBEDDING_DIM = 4096

Env vars used:
    HUGGINGFACEHUB_API_TOKEN - Single HF token
    HF_API_KEYS              - Comma-separated tokens (preferred)
"""

from __future__ import annotations

import os
import re
import time
from backend.logging_config import get_logger
from .api_key_manager import get_hf_key_manager

logger = get_logger("backend.embeddings")

EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
EMBEDDING_DIM = 4096

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

_RETRYABLE = re.compile(r"429|402|rate limit|too many|depleted|credits|payment required")


from langchain_core.embeddings import Embeddings


class LoadBalancedEmbeddings(Embeddings):
    """
    Wrapper around HuggingFaceEndpointEmbeddings that rotates API keys
    on rate limit errors.
    
    Each call to embed_documents or embed_query gets a fresh key from the
    key manager. On rate limit, it retries with the next key.
    """

    def __init__(self):
        self._key_manager = get_hf_key_manager()
        self._model = EMBEDDING_MODEL
        self._task = "feature-extraction"

    def _get_client(self):
        from langchain_huggingface import HuggingFaceEndpointEmbeddings

        api_key = self._key_manager.get_key()
        return HuggingFaceEndpointEmbeddings(
            model=self._model,
            task=self._task,
            huggingfacehub_api_token=api_key,
        ), api_key

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents with retry and key rotation."""
        last_error = None

        for attempt in range(MAX_RETRIES):
            client, api_key = self._get_client()
            try:
                result = client.embed_documents(texts)
                self._key_manager.report_success(api_key)
                return result
            except Exception as e:
                last_error = e
                self._key_manager.report_error(api_key, e)

                if _RETRYABLE.search(str(e)) and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Embeddings error (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue

                raise

        raise last_error

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query with retry and key rotation."""
        last_error = None

        for attempt in range(MAX_RETRIES):
            client, api_key = self._get_client()
            try:
                result = client.embed_query(text)
                self._key_manager.report_success(api_key)
                return result
            except Exception as e:
                last_error = e
                self._key_manager.report_error(api_key, e)

                if _RETRYABLE.search(str(e)) and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Embeddings rate limit (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue

                raise

        raise last_error


_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    hf_keys_env = os.getenv("HF_API_KEYS", "")

    if not token and not hf_keys_env:
        raise ValueError(
            "HUGGINGFACEHUB_API_TOKEN not set. Add your HF token to .env"
        )

    _embeddings = LoadBalancedEmbeddings()
    logger.info("Embeddings ready — model=%s, dim=%d (load-balanced)", EMBEDDING_MODEL, EMBEDDING_DIM)
    return _embeddings
