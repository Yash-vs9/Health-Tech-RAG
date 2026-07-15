"""
Tests for chat routes API.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

auth_headers = {"Authorization": "Bearer test-token"}


class TestChatRoutes:
    """Tests for chat session management routes."""

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_create_chat_success(self, mock_auth, mock_session):
        """Test creating a new chat session."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.create_chat_session = AsyncMock(return_value={
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "My Mortgage Chat",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        })
        
        response = client.post("/chats", json={"title": "My Mortgage Chat"}, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "chat-123"
        assert data["title"] == "My Mortgage Chat"
        assert data["user_id"] == "test-user-123"

    def test_create_chat_unauthorized(self):
        """Test creating chat without authentication."""
        response = client.post("/chats", json={"title": "Test Chat"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_list_chats(self, mock_auth, mock_session):
        """Test listing user's chat sessions."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.get_user_sessions = AsyncMock(return_value=[
            {
                "id": "chat-1",
                "user_id": "test-user-123",
                "title": "First Chat",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
            },
            {
                "id": "chat-2",
                "user_id": "test-user-123",
                "title": "Second Chat",
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T10:00:00Z",
            },
        ])
        
        response = client.get("/chats", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "chat-1"
        assert data[1]["title"] == "Second Chat"

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_get_chat_by_id(self, mock_auth, mock_session):
        """Test getting a specific chat session."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.get_session = AsyncMock(return_value={
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "Test Chat",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        })
        
        response = client.get("/chats/chat-123", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "chat-123"
        assert data["title"] == "Test Chat"

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_update_chat_title(self, mock_auth, mock_session):
        """Test renaming a chat session."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.update_session = AsyncMock(return_value={
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "Updated Title",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T13:00:00Z",
        })
        
        response = client.patch(
            "/chats/chat-123",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

    @patch("backend.routes.chat_routes.vectorstore")
    @patch("backend.routes.chat_routes.message_service")
    @patch("backend.routes.chat_routes.document_service")
    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_delete_chat(
        self, mock_auth, mock_session, mock_doc_service,
        mock_msg_service, mock_vectorstore
    ):
        """Test deleting a chat session (cascades to docs, messages, vectors)."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.get_session = AsyncMock(return_value={
            "id": "chat-123",
            "user_id": "test-user-123",
            "title": "Test Chat",
        })
        mock_session.delete_session = AsyncMock(return_value=True)
        mock_doc_service.delete_chat_documents = AsyncMock(return_value=5)
        mock_msg_service.delete_chat_messages = AsyncMock(return_value=10)
        mock_vectorstore.delete_collection = AsyncMock()
        
        response = client.delete("/chats/chat-123", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["deleted_documents"] == 5
        assert data["deleted_messages"] == 10

    @patch("backend.routes.chat_routes.session_service")
    @patch("backend.routes.chat_routes.auth_service")
    def test_delete_chat_not_found(self, mock_auth, mock_session):
        """Test deleting non-existent chat."""
        mock_auth.get_current_user = AsyncMock(return_value={
            "id": "test-user-123", "email": "test@example.com"
        })
        mock_session.get_session = AsyncMock(return_value=None)
        
        response = client.delete("/chats/non-existent", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND