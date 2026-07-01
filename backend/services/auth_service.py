"""
Auth service.

Wraps Supabase Auth for:
- Email/password signup + login
- Google OAuth (redirect-based flow)
- JWT verification (used as a FastAPI dependency to protect routes)
"""
from __future__ import annotations

import os
from fastapi import HTTPException, Header
from backend.db.supabase_client import get_anon_client, get_admin_client
from backend.logging_config import get_logger

logger = get_logger("backend.auth")


# ── Signup / Login (email + password) ──────────────────────────────────────

def signup_with_email(email: str, password: str, full_name: str | None = None) -> dict:
    client = get_anon_client()
    try:
        result = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}} if full_name else {},
        })
    except Exception as e:
        logger.warning("Signup failed — email=%s, error=%s", email, e)
        raise HTTPException(status_code=400, detail=str(e))

    if result.user is None:
        raise HTTPException(status_code=400, detail="Signup failed — no user returned")

    logger.info("User signed up — id=%s, email=%s", result.user.id, email)

    # Supabase may require email confirmation depending on project settings.
    # If session is None, the user must confirm their email before login.
    if result.session is None:
        return {
            "user_id": result.user.id,
            "email": email,
            "requires_email_confirmation": True,
        }

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "user_id": result.user.id,
        "email": email,
        "full_name": full_name,
    }


def login_with_email(email: str, password: str) -> dict:
    client = get_anon_client()
    try:
        result = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        logger.warning("Login failed — email=%s, error=%s", email, e)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if result.user is None or result.session is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    logger.info("User logged in — id=%s, email=%s", result.user.id, email)

    full_name = (result.user.user_metadata or {}).get("full_name")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "user_id": result.user.id,
        "email": email,
        "full_name": full_name,
    }


def refresh_session(refresh_token: str) -> dict:
    client = get_anon_client()
    try:
        result = client.auth.refresh_session(refresh_token)
    except Exception as e:
        logger.warning("Token refresh failed — error=%s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if result.session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "user_id": result.user.id,
        "email": result.user.email,
        "full_name": (result.user.user_metadata or {}).get("full_name"),
    }


def logout(access_token: str) -> None:
    client = get_anon_client()
    try:
        client.auth.sign_out()
    except Exception as e:
        logger.warning("Logout error (non-fatal) — error=%s", e)


# ── Google OAuth ──────────────────────────────────────────────────────────

def get_google_oauth_url(redirect_to: str) -> str:
    """
    Returns the URL the frontend should redirect the browser to.
    Supabase handles the Google OAuth dance and redirects back to
    `redirect_to` with tokens in the URL fragment.

    Google OAuth provider must be enabled + configured in:
    Supabase Dashboard → Authentication → Providers → Google
    (Client ID + Secret from Google Cloud Console)
    """
    client = get_anon_client()
    result = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": redirect_to},
    })
    return result.url


# ── Token verification (FastAPI dependency) ────────────────────────────────

async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency. Extracts and verifies the JWT from the
    Authorization: Bearer <token> header. Use on any protected route:

        @app.get("/me")
        async def me(user: dict = Depends(get_current_user)):
            return user
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    admin_client = get_admin_client()

    try:
        result = admin_client.auth.get_user(token)
    except Exception as e:
        logger.warning("Token verification failed — error=%s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if result.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "id": result.user.id,
        "email": result.user.email,
        "full_name": (result.user.user_metadata or {}).get("full_name"),
    }
