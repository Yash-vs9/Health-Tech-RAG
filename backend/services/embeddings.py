from __future__ import annotations

import os

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    provider = os.getenv("EMBEDDING_PROVIDER", "local")

    if provider == "api":
        from langchain_huggingface import HuggingFaceEndpointEmbeddings
        model = os.getenv("API_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set. Set EMBEDDING_PROVIDER=local or add your HF token.")
        _embeddings = HuggingFaceEndpointEmbeddings(
            model=model,
            task="feature-extraction",
            huggingfacehub_api_token=token,
        )
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        model = os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embeddings = HuggingFaceEmbeddings(model_name=model)

    return _embeddings
