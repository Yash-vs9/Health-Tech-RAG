"""
Tests for document routes API.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

auth_headers = {"Authorization": "Bearer test-token"}


class TestDocumentRoutes:
    """Tests for document upload and management routes."""

    @patch("backend.routes.document_routes.ingestion")
    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.session_service")
    def test_upload_document_success(self, mock_session, mock_doc_service, mock_ingestion, override_auth):
        """Test successful document upload."""
        mock_session.get_chat_session.return_value = {"id": "chat-789"}
        mock_doc_service.create_document_row.return_value = {
            "id": "row-123",
            "doc_id": "doc-456",
            "chat_session_id": "chat-789",
            "filename": "mortgage.pdf",
            "status": "processing",
            "uploaded_at": "2024-01-01T00:00:00Z",
        }
        mock_ingestion.ingest_document.return_value = {"num_chunks": 10, "num_tables": 0}
        mock_doc_service.upload_to_storage.return_value = "u1/doc_456_mortgage.pdf"

        test_content = b"Test mortgage document content"
        files = {"file": ("mortgage.pdf", test_content, "application/pdf")}

        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filename"] == "mortgage.pdf"
        assert data["status"] == "processing"

    def test_upload_document_no_file(self, override_auth):
        """Test upload without file — missing file returns 422."""
        response = client.post(
            "/chats/chat-789/documents",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_upload_document_invalid_type(self, override_auth):
        """Test upload with invalid file type."""
        files = {"file": ("test.exe", b"executable content", "application/octet-stream")}

        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Only PDF and DOCX files are accepted" in data["detail"]

    @patch("backend.routes.document_routes.document_service")
    def test_list_documents(self, mock_doc_service, override_auth):
        """Test listing documents in a chat."""
        mock_doc_service.list_documents.return_value = [
            {
                "id": "doc-1",
                "doc_id": "doc-a",
                "chat_session_id": "chat-123",
                "filename": "mortgage1.pdf",
                "status": "ready",
                "num_chunks": 5,
                "uploaded_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "doc-2",
                "doc_id": "doc-b",
                "chat_session_id": "chat-123",
                "filename": "mortgage2.pdf",
                "status": "processing",
                "num_chunks": 0,
                "uploaded_at": "2024-01-02T00:00:00Z",
            },
        ]

        response = client.get("/chats/chat-123/documents", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "mortgage1.pdf"
        assert data[1]["status"] == "processing"

    @patch("backend.routes.document_routes.vectorstore")
    @patch("backend.routes.document_routes.document_service")
    def test_delete_document(self, mock_doc_service, mock_vectorstore, override_auth):
        """Test deleting a document."""
        mock_doc_service.delete_document.return_value = {
            "id": "doc-123",
            "doc_id": "doc-456",
            "storage_path": "u1/doc_456.pdf",
        }

        response = client.delete("/chats/chat-123/documents/doc-123", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "deleted"
        assert data["doc_id"] == "doc-456"

    @patch("backend.routes.document_routes.document_service")
    def test_delete_document_not_found(self, mock_doc_service, override_auth):
        """Test deleting non-existent document."""
        mock_doc_service.delete_document.side_effect = ValueError("Document not found or not owned by user")

        response = client.delete("/chats/chat-123/documents/non-existent", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("backend.routes.document_routes.get_admin_client")
    @patch("backend.routes.document_routes.document_service")
    def test_get_document_pdf(self, mock_doc_service, mock_get_admin, override_auth):
        """Test serving PDF document for viewer."""
        mock_doc_service.get_document.return_value = {
            "id": "doc-123",
            "filename": "mortgage.pdf",
            "doc_id": "doc-456",
            "storage_path": "u1/doc_456_mortgage.pdf",
        }

        mock_file_content = b"%PDF-1.4 test pdf content"
        mock_client = MagicMock()
        mock_get_admin.return_value = mock_client
        mock_client.storage.from_.return_value.download.return_value = mock_file_content

        response = client.get("/chats/chat-123/documents/doc-123/pdf", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == mock_file_content

    @patch("backend.routes.document_routes.document_service")
    def test_get_document_pdf_not_found(self, mock_doc_service, override_auth):
        """Test serving non-existent PDF."""
        mock_doc_service.get_document.side_effect = ValueError("Document not found or not owned by user")

        response = client.get("/chats/chat-123/documents/doc-123/pdf", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("backend.routes.document_routes.ingestion")
    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.session_service")
    def test_upload_image_file(self, mock_session, mock_doc_service, mock_ingestion, override_auth):
        """Test uploading image file (JPG/PNG)."""
        mock_session.get_chat_session.return_value = {"id": "chat-789"}
        mock_doc_service.create_document_row.return_value = {
            "id": "row-img-123",
            "doc_id": "doc-img-456",
            "chat_session_id": "chat-789",
            "filename": "chart.png",
            "status": "processing",
            "uploaded_at": "2024-01-01T00:00:00Z",
        }
        mock_ingestion.ingest_document.return_value = {"num_chunks": 1, "num_tables": 0}
        mock_doc_service.upload_to_storage.return_value = "u1/doc_img_chart.png"

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
        assert data["status"] == "processing"

    @patch("backend.routes.document_routes.ingestion")
    @patch("backend.routes.document_routes.document_service")
    @patch("backend.routes.document_routes.session_service")
    def test_upload_docx_file(self, mock_session, mock_doc_service, mock_ingestion, override_auth):
        """Test uploading DOCX file."""
        mock_session.get_chat_session.return_value = {"id": "chat-789"}
        mock_doc_service.create_document_row.return_value = {
            "id": "row-docx-123",
            "doc_id": "doc-docx-456",
            "chat_session_id": "chat-789",
            "filename": "terms.docx",
            "status": "processing",
            "uploaded_at": "2024-01-01T00:00:00Z",
        }
        mock_ingestion.ingest_document.return_value = {"num_chunks": 3, "num_tables": 0}
        mock_doc_service.upload_to_storage.return_value = "u1/doc_docx_terms.docx"

        files = {"file": ("terms.docx", b"docx content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

        response = client.post(
            "/chats/chat-789/documents",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filename"] == "terms.docx"
