"""
Multi-provider LLM wrapper with load balancing.

Supports 4 LLM providers via the LLM_PROVIDER env var:
    nvidia  - NVIDIA NIM (load-balanced via APIKeyManager)
    gemini  - Google Gemini
    hf      - HuggingFace Inference API (load-balanced)
    ollama  - Local Ollama

Classes:
    LoadBalancedNVIDIAChat   - NVIDIA NIM with key rotation and retry
    LoadBalancedHuggingFaceChat - HuggingFace with key rotation and retry

Functions:
    get_llm() -> BaseChatModel  (singleton, initialized on first call)

Env vars used:
    LLM_PROVIDER, NVIDIA_API_KEY(S), NVIDIA_MODEL, NVIDIA_TOP_P, NVIDIA_MAX_TOKENS
    LLM_TEMPERATURE, LLM_TIMEOUT
    GOOGLE_API_KEY, GEMINI_MODEL
    HF_LLM_MODEL, HF_LLM_MAX_TOKENS
    OLLAMA_MODEL, OLLAMA_BASE_URL
"""

from __future__ import annotations

import os
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from backend.logging_config import get_logger
from .api_key_manager import get_nvidia_key_manager, get_hf_key_manager

logger = get_logger("backend.llm")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


class LoadBalancedNVIDIAChat(BaseChatModel):
    """
    LangChain ChatModel that wraps ChatNVIDIA with API key load balancing.

    On each _generate(), it gets a key from the key manager, creates a fresh
    ChatNVIDIA instance, and calls it. On rate limit, retries with the next key.
    """

    _key_manager: Any = None

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        pass

    @property
    def _llm_type(self) -> str:
        return "load-balanced-nvidia"

    @property
    def _identifying_params(self) -> dict:
        return {
            "model": os.getenv("NVIDIA_MODEL", "nvidia/nemotron-nano-9b-v2"),
            "provider": "nvidia",
            "load_balanced": True,
        }

    def _get_key_manager(self):
        if self._key_manager is None:
            self._key_manager = get_nvidia_key_manager()
        return self._key_manager

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        km = self._get_key_manager()
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-nano-9b-v2")
        top_p = float(os.getenv("NVIDIA_TOP_P", "0.95"))
        max_tokens = int(os.getenv("NVIDIA_MAX_TOKENS", "4096"))

        last_error = None
        for attempt in range(MAX_RETRIES):
            api_key = km.get_key()
            try:
                timeout = int(os.getenv("LLM_TIMEOUT", "120"))
                llm = ChatNVIDIA(
                    model=model,
                    api_key=api_key,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                result = llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                km.report_success(api_key)
                return result
            except Exception as e:
                last_error = e
                km.report_error(api_key, e)
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "too many" in err_str
                is_timeout = "timeout" in err_str or "timed out" in err_str
                
                if is_timeout and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "NVIDIA timeout (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                elif is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "NVIDIA rate limit (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                raise
        raise last_error

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # For now, fall back to sync _generate
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class LoadBalancedHuggingFaceChat(BaseChatModel):
    """
    LangChain ChatModel that wraps HuggingFace Inference API with key load balancing.
    """

    _key_manager: Any = None

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        pass

    @property
    def _llm_type(self) -> str:
        return "load-balanced-huggingface"

    @property
    def _identifying_params(self) -> dict:
        return {
            "model": os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            "provider": "huggingface",
            "load_balanced": True,
        }

    def _get_key_manager(self):
        if self._key_manager is None:
            self._key_manager = get_hf_key_manager()
        return self._key_manager

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        from huggingface_hub import InferenceClient

        km = self._get_key_manager()
        model = os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        max_tokens = int(os.getenv("HF_LLM_MAX_TOKENS", "1024"))

        # Convert messages to HF format
        hf_messages = []
        for msg in messages:
            role = "user"
            if hasattr(msg, "type"):
                if msg.type == "system":
                    role = "system"
                elif msg.type == "ai":
                    role = "assistant"
            hf_messages.append({"role": role, "content": msg.content})

        last_error = None
        for attempt in range(MAX_RETRIES):
            api_key = km.get_key()
            try:
                client = InferenceClient(api_key=api_key)
                completion = client.chat.completions.create(
                    model=model,
                    messages=hf_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = completion.choices[0].message.content
                km.report_success(api_key)
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=content))]
                )
            except Exception as e:
                last_error = e
                km.report_error(api_key, e)
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "too many" in err_str
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "HuggingFace rate limit (attempt %d/%d) — retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
                raise
        raise last_error

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


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
        _llm = LoadBalancedNVIDIAChat()
        logger.info(
            "LLM ready — NVIDIA (load-balanced, model=%s)",
            os.getenv("NVIDIA_MODEL", "nvidia/nemotron-nano-9b-v2"),
        )

    elif provider == "hf":
        _llm = LoadBalancedHuggingFaceChat()
        logger.info(
            "LLM ready — HuggingFace (load-balanced, model=%s)",
            os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        )

    else:
        from langchain_community.llms import Ollama
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _llm = Ollama(model=model, base_url=base_url, temperature=temperature)
        logger.info("LLM ready — Ollama model=%s, base_url=%s", model, base_url)

    return _llm
