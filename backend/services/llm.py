from __future__ import annotations

import os
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun


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

        client = InferenceClient(api_key=self.api_key)

        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return completion.choices[0].message.content

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

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        _llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)

    elif provider == "hf":
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set.")
        model = os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        _llm = HuggingFaceLLM(
            model=model,
            api_key=token,
            temperature=temperature,
            max_tokens=1024,
        )

    else:
        from langchain_community.llms import Ollama
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _llm = Ollama(model=model, base_url=base_url, temperature=temperature)

    return _llm
