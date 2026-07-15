"""
Tests for document routes API.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

auth_headers = {"Authorization": "Bearer test-token"}


class TestDocumentRoutes:
    """Tests for document upload and management routes."""

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_upload_document_success(self, mock_auth, mock_doc_service):
        """Test successful document upload."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.upload_document = AsyncMock(return_value={
            "id": "doc-123",
            "doc_id": "doc-456",
            "chat_session_id": "chat-789",
            "filename": "mortgage.pdf",
            "status": "ready",
            "chunks": 10,
            "created_at": "2024-01-01T00:00:00Z",
        })
        
        test_content = b"Test mortgage document content"
        files = {"file": ("mortgage.pdf", test_content, "application/pdf")}
        
        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "doc-123"
        assert data["filename"] == "mortgage.pdf"
        assert data["status"] == "ready"

    def test_upload_document_no_file(self):
        """Test upload without file."""
        response = client.post(
            "/chats/chat-789/documents",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_upload_document_invalid_type(self, mock_auth, mock_doc_service):
        """Test upload with invalid file type."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        
        files = {"file": ("test.exe", b"executable content", "application/octet-stream")}
        
        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Unsupported file type" in data["detail"]

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_list_documents(self, mock_auth, mock_doc_service):
        """Test listing documents in a chat."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.get_chat_documents = AsyncMock(return_value=[
            {
                "id": "doc-1",
                "doc_id": "doc-a",
                "chat_session_id": "chat-123",
                "filename": "mortgage1.pdf",
                "status": "ready",
                "chunks": 5,
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "doc-2",
                "doc_id": "doc-b",
                "chat_session_id": "chat-123",
                "filename": "mortgage2.pdf",
                "status": "processing",
                "chunks": 0,
                "created_at": "2024-01-02T00:00:00Z",
            },
        ])
        
        response = client.get("/chats/chat-123/documents", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "mortgage1.pdf"
        assert data[1]["status"] == "processing"

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_delete_document(self, mock_auth, mock_doc_service):
        """Test deleting a document."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.delete_document = AsyncMock(return_value=True)
        
        response = client.delete("/chats/chat-123/documents/doc-123", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_delete_document_not_found(self, mock_auth, mock_doc_service):
        """Test deleting non-existent document."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.delete_document = AsyncMock(return_value=False)
        
        response = client.delete("/chats/chat-123/documents/non-existent", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_get_document_pdf(self, mock_auth, mock_doc_service):
        """Test serving PDF document for viewer."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        
        mock_file_content = b"%PDF-1.4 test pdf content"
        mock_doc_service.get_document_file = AsyncMock(return_value=mock_file_content)
        mock_doc_service.get_document = AsyncMock(return_value={
            "id": "doc-123",
            "filename": "mortgage.pdf",
            "doc_id": "doc-456",
        })
        
        response = client.get("/chats/chat-123/documents/doc-123/pdf", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == mock_file_content

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_get_document_pdf_not_found(self, mock_auth, mock_doc_service):
        """Test serving non-existent PDF."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.get_document_file = AsyncMock(return_value=None)
        
        response = client.get("/chats/chat-123/documents/doc-123/pdf", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_upload_image_file(self, mock_auth, mock_doc_service):
        """Test uploading image file (JPG/PNG)."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.upload_document = AsyncMock(return_value={
            "id": "doc-img-123",
            "doc_id": "doc-img-456",
            "chat_session_id": "chat-789",
            "filename": "chart.png",
            "status": "ready",
            "chunks": 1,
            "created_at": "2024-01-01T00:00:00Z",
        })
        
        # Minimal valid PNG
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        files = {"file": ("chart.png", png_header, "image/png")}
        
        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filename"] == "chart.png"
        assert data["status"] == "ready"

    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.auth_service")
    def test_upload_docx_file(self, mock_auth, mock_doc_service):
        """Test uploading DOCX file."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_doc_service.upload_document = AsyncMock(return_value={
            "id": "doc-docx-123",
            "doc_id": "doc-docx-456",
            "chat_session_id": "chat-789",
            "filename": "terms.docx",
            "status": "ready",
            "chunks": 3,
            "created_at": "2024-01-01T00:00:00Z",
        })
        
        files = {"file": ("terms.docx", b"docx content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filename"] == "terms.docx"