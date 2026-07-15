"""
Shared pytest fixtures and configuration for backend tests.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "NVIDIA_API_KEY": "test-nvidia-key",
        "NVIDIA_API_KEYS": "test-nvidia-key-1,test-nvidia-key-2",
        "NVIDIA_MODEL": "nvidia/nemotron-nano-9b-v2",
        "NVIDIA_TOP_P": "0.95",
        "NVIDIA_MAX_TOKENS": "4096",
        "NVIDIA_KEY_COOLDOWN": "60",
        "HUGGINGFACEHUB_API_TOKEN": "test-hf-token",
        "HF_API_KEYS": "test-hf-token-1,test-hf-token-2",
        "HF_KEY_COOLDOWN": "60",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SUPABASE_STORAGE_BUCKET": "documents",
        "INPUT_GUARDRAILS_ENABLED": "true",
        "OUTPUT_GUARDRAILS_ENABLED": "true",
        "NEMO_GUARDRAILS_ENABLED": "true",
        "MAX_UPLOAD_BYTES": "26214400",
        "ALLOW_RESET_COLLECTION": "false",
        "RETRIEVER_TOP_K": "10",
        "MULTI_QUERY_ENABLED": "true",
        "MULTI_QUERY_N": "3",
        "RERANK_ENABLED": "true",
        "LLM_TEMPERATURE": "0.0",
        "CHUNK_SIZE": "1024",
        "CHUNK_OVERLAP": "50",
        "VISION_MODEL": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        "VISION_TIMEOUT": "120",
        "VISION_DELAY": "2",
        "VISION_PDF_ENABLED": "true",
        "VISION_PDF_PAGE_LIMIT": "0",
        "VISION_PDF_ZOOM": "1.5",
        "VISION_DOCX_ENABLED": "true",
        "VISION_DOCX_IMAGE_LIMIT": "10",
        "OCR_FALLBACK_ENABLED": "true",
        "OCR_MIN_CHARS_PER_PAGE": "40",
        "OCR_LANGUAGE": "eng",
        "OCR_ZOOM": "2.0",
        "TESSERACT_CMD": "",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def mock_nvidia_key_manager():
    """Mock NVIDIA API key manager."""
    with patch("backend.services.llm.get_nvidia_key_manager") as mock:
        manager = MagicMock()
        manager.get_key.return_value = "test-nvidia-key"
        manager.report_success = MagicMock()
        manager.report_error = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_hf_key_manager():
    """Mock HuggingFace API key manager."""
    with patch("backend.services.embeddings.get_hf_key_manager") as mock:
        manager = MagicMock()
        manager.get_key.return_value = "test-hf-token"
        manager.report_success = MagicMock()
        manager.report_error = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("backend.db.supabase_client.get_admin_client") as mock_admin, \
         patch("backend.db.supabase_client.get_anon_client") as mock_anon:
        
        admin_client = MagicMock()
        anon_client = MagicMock()
        mock_admin.return_value = admin_client
        mock_anon.return_value = anon_client
        
        yield {
            "admin": admin_client,
            "anon": anon_client,
        }


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    from langchain_core.documents import Document
    return Document(
        page_content="This is a test mortgage document with loan terms and rates.",
        metadata={
            "source": "test_mortgage.pdf",
            "page": 1,
            "section": "Loan Terms",
            "doc_id": "test-doc-123",
        }
    )


@pytest.fixture
def sample_documents():
    """Create multiple sample documents for testing."""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="PNB Housing loan has 8.5% interest rate.",
            metadata={"source": "pnb_housing.pdf", "page": 1, "doc_id": "doc-1"}
        ),
        Document(
            page_content="HDFC loan processing fee is 0.5%.",
            metadata={"source": "hdfc.pdf", "page": 2, "doc_id": "doc-2"}
        ),
        Document(
            page_content="ICICI bank offers 9% fixed rate for 20 years.",
            metadata={"source": "icici.pdf", "page": 1, "doc_id": "doc-3"}
        ),
    ]


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB vectorstore."""
    with patch("backend.services.vectorstore.get_vectorstore") as mock:
        vectorstore = MagicMock()
        vectorstore.similarity_search.return_value = []
        vectorstore.add_documents = MagicMock()
        vectorstore.delete = MagicMock()
        mock.return_value = vectorstore
        yield vectorstore


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model."""
    with patch("backend.services.embeddings.get_embeddings") as mock:
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = [[0.1] * 4096]
        embeddings.embed_query.return_value = [0.1] * 4096
        mock.return_value = embeddings
        yield embeddings


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    with patch("backend.services.llm.get_llm") as mock:
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(
            content="This is a test response from the LLM."
        )
        mock.return_value = llm
        yield llm


# Override auth dependency for testing
@pytest.fixture(autouse=True)
def override_auth():
    """Override the auth dependency for testing."""
    from backend.main import app
    from backend.services.auth_service import get_current_user
    
    def mock_get_current_user():
        return {"id": "test-user-123", "email": "test@example.com"}
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    yield
    
    # Clean up
    app.dependency_overrides.clear()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_api: Tests that require external API keys")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on path."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark slow tests
        if "evaluation" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
        # Mark tests requiring API
        if "api" in str(item.fspath) or "vision" in str(item.fspath):
            item.add_marker(pytest.mark.requires_api)