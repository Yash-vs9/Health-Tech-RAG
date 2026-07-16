"""
Tests for chat routes API.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

auth_headers = {"Authorization": "Bearer test-token"}


class TestChatRoutes:
    """Tests for chat session management routes."""

    @patch("backend.routes.chat_routes.session_service")
    def test_create_chat_success(self, mock_session, override_auth):
        """Test creating a new chat session."""
        mock_session.create_chat_session.return_value = {
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "My Mortgage Chat",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "document_count": 0,
        }

        response = client.post("/chats", json={"title": "My Mortgage Chat"}, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "chat-123"
        assert data["title"] == "My Mortgage Chat"

    def test_create_chat_unauthorized(self):
        """Test creating chat without authentication — missing header returns 422."""
        response = client.post("/chats", json={"title": "Test Chat"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @patch("backend.routes.chat_routes.session_service")
    def test_list_chats(self, mock_session, override_auth):
        """Test listing user's chat sessions."""
        mock_session.list_chat_sessions.return_value = [
            {
                "id": "chat-1",
                "user_id": "test-user-123",
                "title": "First Chat",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "document_count": 0,
            },
            {
                "id": "chat-2",
                "user_id": "test-user-123",
                "title": "Second Chat",
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T10:00:00Z",
                "document_count": 0,
            },
        ]

        response = client.get("/chats", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "chat-1"
        assert data[1]["title"] == "Second Chat"

    @patch("backend.routes.chat_routes.session_service")
    def test_get_chat_by_id(self, mock_session, override_auth):
        """Test getting a specific chat session."""
        mock_session.get_chat_session.return_value = {
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "Test Chat",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        }

        response = client.get("/chats/chat-123", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "chat-123"
        assert data["title"] == "Test Chat"

    @patch("backend.routes.chat_routes.session_service")
    def test_update_chat_title(self, mock_session, override_auth):
        """Test renaming a chat session."""
        mock_session.rename_chat_session.return_value = {
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "Updated Title",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T13:00:00Z",
        }

        response = client.patch(
            "/chats/chat-123",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.services.vectorstore")
    @patch("backend.services.document_service")
    def test_delete_chat(
        self, mock_doc_service, mock_vectorstore, mock_session, override_auth,
    ):
        """Test deleting a chat session."""
        mock_doc_service.list_documents.return_value = [
            {"doc_id": "doc-a", "id": "row-1", "storage_path": "u1/doc_a.pdf"},
            {"doc_id": "doc-b", "id": "row-2", "storage_path": None},
        ]
        mock_doc_service.BUCKET = "documents"

        response = client.delete("/chats/chat-123", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "deleted"
        assert data["documents_cleaned"] == 2
        mock_session.delete_chat_session.assert_called_once()

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.services.document_service")
    def test_delete_chat_not_found(self, mock_doc_service, mock_session, override_auth):
        """Test deleting non-existent chat."""
        mock_doc_service.list_documents.return_value = []
        mock_session.delete_chat_session.side_effect = ValueError("Chat session not found or not owned by user")

        response = client.delete("/chats/non-existent", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
