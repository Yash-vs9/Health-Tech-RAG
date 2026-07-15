import os
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest
from langchain_core.messages import HumanMessage

from backend.services.ingestion import (
    _get_vision_provider_and_key,
    _call_vision_model,
)

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure environment is clean before/after each test."""
    old_env = dict(os.environ)
    # Remove keys we are testing
    os.environ.pop("VISION_PROVIDER", None)
    os.environ.pop("LLM_PROVIDER", None)
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_API_KEYS", None)
    yield
    os.environ.clear()
    os.environ.update(old_env)


def test_get_vision_provider_and_key_explicit_gemini():
    os.environ["VISION_PROVIDER"] = "gemini"
    os.environ["GOOGLE_API_KEY"] = "fake-google-key"
    
    provider, key = _get_vision_provider_and_key()
    assert provider == "gemini"
    assert key == "fake-google-key"


def test_get_vision_provider_and_key_explicit_nvidia():
    os.environ["VISION_PROVIDER"] = "nvidia"
    os.environ["NVIDIA_API_KEY"] = "fake-nvidia-key"
    
    provider, key = _get_vision_provider_and_key()
    assert provider == "nvidia"
    assert key == "fake-nvidia-key"


def test_get_vision_provider_and_key_fallback_llm_provider():
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["GOOGLE_API_KEY"] = "fake-google-key"
    
    provider, key = _get_vision_provider_and_key()
    assert provider == "gemini"
    assert key == "fake-google-key"


def test_get_vision_provider_and_key_auto_detect_google():
    os.environ["GOOGLE_API_KEY"] = "fake-google-key"
    
    provider, key = _get_vision_provider_and_key()
    assert provider == "gemini"
    assert key == "fake-google-key"


def test_get_vision_provider_and_key_auto_detect_nvidia():
    os.environ["NVIDIA_API_KEY"] = "fake-nvidia-key"
    
    provider, key = _get_vision_provider_and_key()
    assert provider == "nvidia"
    assert key == "fake-nvidia-key"


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_call_vision_model_gemini(mock_chat_class):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Gemini vision output")
    mock_chat_class.return_value = mock_llm

    os.environ["VISION_PROVIDER"] = "gemini"
    os.environ["GOOGLE_API_KEY"] = "fake-google-key"
    os.environ["VISION_MODEL"] = "gemini-1.5-flash"

    img = Image.new("RGB", (100, 100))
    result = _call_vision_model(img, "Describe the image", "test-ctx")

    assert result == "Gemini vision output"
    mock_chat_class.assert_called_once_with(
        model="gemini-1.5-flash",
        google_api_key="fake-google-key",
        temperature=0.0,
    )
    # Check that it invoked the model with a HumanMessage containing text + image_url
    args, _ = mock_llm.invoke.call_args
    messages = args[0]
    assert len(messages) == 1
    msg = messages[0]
    assert isinstance(msg, HumanMessage)
    assert msg.content[0]["text"] == "Describe the image"
    assert msg.content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@patch("langchain_nvidia_ai_endpoints.ChatNVIDIA")
def test_call_vision_model_nvidia(mock_chat_class):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="NVIDIA vision output")
    mock_chat_class.return_value = mock_llm

    os.environ["VISION_PROVIDER"] = "nvidia"
    os.environ["NVIDIA_API_KEY"] = "fake-nvidia-key"
    os.environ["VISION_MODEL"] = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"

    img = Image.new("RGB", (100, 100))
    result = _call_vision_model(img, "Describe the image", "test-ctx")

    assert result == "NVIDIA vision output"
    mock_chat_class.assert_called_once_with(
        model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        api_key="fake-nvidia-key",
        temperature=0.0,
        max_tokens=2048,
    )
