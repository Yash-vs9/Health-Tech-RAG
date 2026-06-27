from __future__ import annotations

import os

_llm = None


def get_llm():
    global _llm
    if _llm is not None:
        return _llm

    provider = os.getenv("LLM_PROVIDER", "ollama")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        _llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)

    elif provider == "hf":
        from langchain_huggingface import HuggingFaceEndpoint
        model = os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set.")
        _llm = HuggingFaceEndpoint(
            repo_id=model,
            task="conversational",
            huggingfacehub_api_token=token,
            temperature=temperature,
            max_new_tokens=1024,
        )

    else:
        from langchain_community.llms import Ollama
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _llm = Ollama(model=model, base_url=base_url, temperature=temperature)

    return _llm
