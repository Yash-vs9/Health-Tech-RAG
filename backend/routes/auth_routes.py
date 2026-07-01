from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from backend.models.schemas import (
    SignupRequest, LoginRequest, AuthResponse,
    GoogleOAuthURLResponse, RefreshTokenRequest, UserProfile,
)
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    result = auth_service.signup_with_email(req.email, req.password, req.full_name)
    return result


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    result = auth_service.login_with_email(req.email, req.password)
    return result


@router.post("/refresh", response_model=AuthResponse)
async def refresh(req: RefreshTokenRequest):
    result = auth_service.refresh_session(req.refresh_token)
    return result


@router.get("/google/url", response_model=GoogleOAuthURLResponse)
async def google_oauth_url(redirect_to: str = Query(..., description="Frontend URL to redirect back to after Google login")):
    """
    Frontend calls this, then does: window.location.href = response.auth_url
    Supabase handles the Google consent screen and redirects back to
    `redirect_to` with access_token/refresh_token in the URL fragment.
    """
    url = auth_service.get_google_oauth_url(redirect_to)
    return {"auth_url": url}


@router.post("/logout")
async def logout(user: dict = Depends(auth_service.get_current_user)):
    return {"status": "logged_out"}


@router.get("/me", response_model=UserProfile)
async def me(user: dict = Depends(auth_service.get_current_user)):
    from backend.db.supabase_client import get_admin_client
    client = get_admin_client()
    result = client.table("profiles").select("*").eq("id", user["id"]).maybe_single().execute()
    return result.data
