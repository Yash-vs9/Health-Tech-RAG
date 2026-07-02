from __future__ import annotations

import os
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from backend.logging_config import get_logger

logger = get_logger("backend.llm")


class HuggingFaceLLM(LLM):
    """LLM wrapper using HuggingFace Inference Client (OpenAI-compatible)."""
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    api_key: str = ""
    temperature: float = 0.0
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "huggingface-inference"

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs,
    ) -> str:
        from huggingface_hub import InferenceClient

        logger.debug("HF LLM call — model=%s, prompt_len=%d", self.model, len(prompt))
        client = InferenceClient(api_key=self.api_key)

        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        response = completion.choices[0].message.content
        logger.debug("HF LLM response — len=%d", len(response))
        return response

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model}


_llm = None


def get_llm():
    global _llm
    if _llm is not None:
        return _llm

    provider = os.getenv("LLM_PROVIDER", "ollama")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    logger.info("Initializing LLM — provider=%s, temperature=%.1f", provider, temperature)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not set")
            raise ValueError("GOOGLE_API_KEY not set.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        _llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)
        logger.info("LLM ready — Gemini model=%s", model)

    elif provider == "nvidia":
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            logger.error("NVIDIA_API_KEY not set")
            raise ValueError("NVIDIA_API_KEY not set.")
        model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-nano-9b-v2")
        _llm = ChatNVIDIA(
            model=model,
            api_key=api_key,
            temperature=temperature,
            top_p=float(os.getenv("NVIDIA_TOP_P", "0.95")),
            max_tokens=int(os.getenv("NVIDIA_MAX_TOKENS", "4096")),
        )
        logger.info("LLM ready — NVIDIA model=%s", model)

    elif provider == "hf":
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            logger.error("HUGGINGFACEHUB_API_TOKEN not set")
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set.")
        model = os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        _llm = HuggingFaceLLM(
            model=model,
            api_key=token,
            temperature=temperature,
            max_tokens=1024,
        )
        logger.info("LLM ready — HuggingFace model=%s", model)

    else:
        from langchain_community.llms import Ollama
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _llm = Ollama(model=model, base_url=base_url, temperature=temperature)
        logger.info("LLM ready — Ollama model=%s, base_url=%s", model, base_url)

    return _llm
