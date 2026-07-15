"""
Tests for NVIDIA vision model integration in ingestion pipeline.
"""
import os
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest

from backend.services.ingestion import (
    _get_vision_api_key,
    _call_vision_model,
)


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure environment is clean before/after each test."""
    old_env = dict(os.environ)
    # Remove keys we are testing
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_API_KEYS", None)
    os.environ.pop("VISION_MODEL", None)
    yield
    os.environ.clear()
    os.environ.update(old_env)


def test_get_vision_api_key_single():
    """Test getting single NVIDIA API key."""
    os.environ["NVIDIA_API_KEY"] = "fake-nvidia-key"
    
    key = _get_vision_api_key()
    assert key == "fake-nvidia-key"


def test_get_vision_api_key_multiple():
    """Test getting first key from comma-separated list."""
    os.environ["NVIDIA_API_KEYS"] = "key1,key2,key3"
    
    key = _get_vision_api_key()
    assert key == "key1"


def test_get_vision_api_key_multiple_with_spaces():
    """Test getting first key with spaces in the list."""
    os.environ["NVIDIA_API_KEYS"] = "key1 , key2 , key3"
    
    key = _get_vision_api_key()
    assert key == "key1"


def test_get_vision_api_key_none():
    """Test returns None when no keys configured."""
    # Ensure no keys in env
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_API_KEYS", None)
    
    key = _get_vision_api_key()
    assert key is None


@patch("langchain_nvidia_ai_endpoints.ChatNVIDIA")
def test_call_vision_model_success(mock_chat_class):
    """Test successful vision model call."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="NVIDIA vision output")
    mock_chat_class.return_value = mock_llm

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
        timeout=120,
    )
    # Check that it invoked the model with a HumanMessage containing text + image_url
    args, _ = mock_llm.invoke.call_args
    messages = args[0]
    assert len(messages) == 1
    msg = messages[0]
    from langchain_core.messages import HumanMessage
    assert isinstance(msg, HumanMessage)
    assert msg.content[0]["text"] == "Describe the image"
    assert msg.content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@patch("langchain_nvidia_ai_endpoints.ChatNVIDIA")
def test_call_vision_model_no_api_key(mock_chat_class):
    """Test vision model returns None when no API key."""
    # Ensure no keys in env
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NVIDIA_API_KEYS", None)

    img = Image.new("RGB", (100, 100))
    result = _call_vision_model(img, "Describe the image", "test-ctx")

    assert result is None
    mock_chat_class.assert_not_called()


@patch("langchain_nvidia_ai_endpoints.ChatNVIDIA")
def test_call_vision_model_exception_handling(mock_chat_class):
    """Test vision model handles exceptions gracefully."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API error")
    mock_chat_class.return_value = mock_llm

    os.environ["NVIDIA_API_KEY"] = "fake-nvidia-key"
    os.environ["VISION_MODEL"] = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"

    img = Image.new("RGB", (100, 100))
    result = _call_vision_model(img, "Describe the image", "test-ctx")

    assert result is None
    mock_chat_class.assert_called_once()