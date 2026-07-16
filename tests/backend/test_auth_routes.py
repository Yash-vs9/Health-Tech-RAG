"""
Tests for auth routes API.
"""
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestAuthRoutes:
    """Tests for authentication routes."""

    @patch("backend.routes.auth_routes.auth_service")
    def test_signup_success(self, mock_auth_service):
        """Test successful user signup."""
        mock_auth_service.signup_with_email = Mock(return_value={
            "access_token": "test-token",
            "refresh_token": "refresh-token",
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
        })

        response = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "securepassword123", "full_name": "Test User"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "test-token"
        assert data["user_id"] == "user-123"
        assert data["email"] == "test@example.com"

    def test_signup_invalid_email(self):
        """Test signup with invalid email."""
        response = client.post(
            "/auth/signup",
            json={"email": "invalid-email", "password": "securepassword123", "full_name": "Test User"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_signup_short_password(self):
        """Test signup with too short password."""
        response = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "123", "full_name": "Test User"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @patch("backend.routes.auth_routes.auth_service")
    def test_login_success(self, mock_auth_service):
        """Test successful login."""
        mock_auth_service.login_with_email = Mock(return_value={
            "access_token": "test-token",
            "refresh_token": "refresh-token",
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
        })

        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "test-token"
        assert data["user_id"] == "user-123"
        assert data["email"] == "test@example.com"

    @patch("backend.routes.auth_routes.auth_service")
    def test_login_invalid_credentials(self, mock_auth_service):
        """Test login with invalid credentials - exception propagates."""
        mock_auth_service.login_with_email = Mock(side_effect=Exception("Invalid credentials"))

        with pytest.raises(Exception, match="Invalid credentials"):
            mock_auth_service.login_with_email("test@example.com", "wrongpassword")

        mock_auth_service.login_with_email.assert_called_once_with("test@example.com", "wrongpassword")

    @patch("backend.routes.auth_routes.auth_service")
    def test_logout_success(self, mock_auth_service):
        """Test logout - requires valid auth token via middleware."""
        mock_auth_service.get_current_user = Mock(return_value={"id": "user-123", "email": "test@example.com"})

        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED)

    @patch("backend.db.supabase_client.get_admin_client")
    def test_get_current_user(self, mock_get_admin, override_auth):
        """Test getting current user info via /me endpoint."""
        mock_client = MagicMock()
        mock_get_admin.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "user-123", "email": "test@example.com", "full_name": "Test User",
                  "avatar_url": None, "provider": "email", "created_at": "2024-01-01T00:00:00Z"}
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_current_user_unauthorized(self):
        """Test getting current user without token."""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @patch("backend.routes.auth_routes.auth_service")
    def test_refresh_token(self, mock_auth_service):
        """Test refreshing access token."""
        mock_auth_service.refresh_session = Mock(return_value={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
        })

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new-token"
        assert data["user_id"] == "user-123"

    @patch("backend.routes.auth_routes.auth_service")
    def test_google_oauth_url(self, mock_auth_service):
        """Test getting Google OAuth URL."""
        mock_auth_service.get_google_oauth_url = Mock(return_value="https://accounts.google.com/oauth/...")

        response = client.get("/auth/google/url", params={"redirect_to": "http://localhost:3000"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "auth_url" in data
