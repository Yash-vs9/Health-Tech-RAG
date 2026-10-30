"""
Multi-provider embeddings with load balancing.

Supports 2 embedding providers via EMBEDDING_PROVIDER env var:
    huggingface - Qwen3-Embedding-8B via HF Inference API (load-balanced)
    nvidia      - Nemotron 3.5 Embed 8B via NVIDIA NIM (load-balanced)

Classes:
    LoadBalancedHuggingFaceEmbeddings - HF endpoint with key rotation
    LoadBalancedNVIDIAEmbeddings      - NVIDIA NIM (OpenAI-compatible) with key rotation

Functions:
    get_embeddings() -> Embeddings  (singleton, initialized on first call)

Constants (per provider):
    HuggingFace: EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B", EMBEDDING_DIM = 4096
    NVIDIA:      EMBEDDING_MODEL = "nvidia/nemotron-3.5-embed-8b", EMBEDDING_DIM = 4096

Env vars used:
    EMBEDDING_PROVIDER           - "huggingface" (default) or "nvidia"
    HUGGINGFACEHUB_API_TOKEN     - Single HF token
    HF_API_KEYS                  - Comma-separated HF tokens (preferred)
    NVIDIA_API_KEY               - Single NVIDIA key
    NVIDIA_API_KEYS              - Comma-separated NVIDIA keys (preferred)
    NVIDIA_EMBEDDING_MODEL       - Override NVIDIA embedding model
    NVIDIA_EMBEDDING_DIM         - Override NVIDIA embedding dimension
"""

from __future__ import annotations

import os
import re
import time
from backend.logging_config import get_logger
from .api_key_manager import get_hf_key_manager, get_nvidia_key_manager

logger = get_logger("backend.embeddings")

# Provider selection
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()

# HuggingFace (Qwen3-Embedding-8B) defaults
HF_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
HF_EMBEDDING_DIM = 4096

# NVIDIA (Nemotron 3.5 Embed 8B) defaults
NVIDIA_EMBEDDING_MODEL = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3.5-embed-1b")
NVIDIA_EMBEDDING_DIM = int(os.getenv("NVIDIA_EMBEDDING_DIM", "2048"))

# Active model/dim based on provider
if EMBEDDING_PROVIDER == "nvidia":
    EMBEDDING_MODEL = NVIDIA_EMBEDDING_MODEL
    EMBEDDING_DIM = NVIDIA_EMBEDDING_DIM
else:
    EMBEDDING_MODEL = HF_EMBEDDING_MODEL
    EMBEDDING_DIM = HF_EMBEDDING_DIM

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

_RETRYABLE = re.compile(r"429|402|rate limit|too many|depleted|credits|payment required")


from langchain_core.embeddings import Embeddings


class LoadBalancedHuggingFaceEmbeddings(Embeddings):
    """
    Wrapper around HuggingFaceEndpointEmbeddings that rotates API keys
    on rate limit errors.
    """

    def __init__(self):
        self._key_manager = get_hf_key_manager()
        self._model = HF_EMBEDDING_MODEL
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
                        "HF embeddings error (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue

                raise

        raise last_error

    def embed_query(self, text: str) -> list[float]:
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
                        "HF embeddings rate limit (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue

                raise

        raise last_error


class LoadBalancedNVIDIAEmbeddings(Embeddings):
    """
    NVIDIA NIM embeddings (OpenAI-compatible) with API key load balancing.
    
    Uses the NVIDIA API at https://integrate.api.nvidia.com/v1 with the
    nemotron-3.5-embed-8b model (4096-dim). Supports text and multimodal
    (text+image) embeddings.
    """

    _key_manager: any = None

    def __init__(self):
        self._model = NVIDIA_EMBEDDING_MODEL
        self._base_url = "https://integrate.api.nvidia.com/v1"
        self._dim = NVIDIA_EMBEDDING_DIM

    def _get_key_manager(self):
        if self._key_manager is None:
            self._key_manager = get_nvidia_key_manager()
        return self._key_manager

    def _get_client(self, api_key: str):
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=self._base_url)

    def _embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        last_error = None
        km = self._get_key_manager()

        for attempt in range(MAX_RETRIES):
            api_key = km.get_key()
            try:
                client = self._get_client(api_key)
                # NVIDIA NIM expects extra_body for modality and input_type
                extra_body = {
                    "modality": ["text"],
                    "input_type": input_type,
                    "truncate": "END"
                }
                response = client.embeddings.create(
                    input=texts,
                    model=self._model,
                    encoding_format="float",
                    extra_body=extra_body,
                )
                km.report_success(api_key)
                return [d.embedding for d in response.data]
            except Exception as e:
                last_error = e
                km.report_error(api_key, e)

                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "too many" in err_str
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "NVIDIA embeddings rate limit (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                # NIM returns 500 "service inference failed" for multi-text batches;
                # single-text requests succeed, so fall back to one at a time.
                if len(texts) > 1 and "500" in err_str:
                    logger.warning(
                        "NVIDIA batch of %d failed with 500 — falling back to single-text requests",
                        len(texts),
                    )
                    return [self._embed([t], input_type)[0] for t in texts]
                raise

        raise last_error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, input_type="passage")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], input_type="query")[0]


_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    if EMBEDDING_PROVIDER == "nvidia":
        keys = os.getenv("NVIDIA_API_KEYS", "")
        single = os.getenv("NVIDIA_API_KEY", "")
        if not keys and not single:
            raise ValueError(
                "NVIDIA_API_KEY or NVIDIA_API_KEYS not set. Add NVIDIA API key(s) to .env"
            )
        _embeddings = LoadBalancedNVIDIAEmbeddings()
        logger.info(
            "Embeddings ready — provider=nvidia, model=%s, dim=%d (load-balanced)",
            EMBEDDING_MODEL, EMBEDDING_DIM
        )
    else:
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        hf_keys_env = os.getenv("HF_API_KEYS", "")
        if not token and not hf_keys_env:
            raise ValueError(
                "HUGGINGFACEHUB_API_TOKEN not set. Add your HF token to .env"
            )
        _embeddings = LoadBalancedHuggingFaceEmbeddings()
        logger.info(
            "Embeddings ready — provider=huggingface, model=%s, dim=%d (load-balanced)",
            EMBEDDING_MODEL, EMBEDDING_DIM
        )
    return _embeddings
