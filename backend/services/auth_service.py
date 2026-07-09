from __future__ import annotations

import os
from fastapi import HTTPException, Header
from backend.db.supabase_client import get_anon_client, get_admin_client
from backend.logging_config import get_logger

logger = get_logger("backend.auth")


def signup_with_email(email: str, password: str, full_name: str | None = None) -> dict:
    admin_client = get_admin_client()
    client = get_anon_client()
    try:
        # Create user via admin API to auto-confirm email
        user_data = {
            "email": email,
            "password": password,
            "email_confirm": True,
        }
        if full_name:
            user_data["user_metadata"] = {"full_name": full_name}
            
        admin_client.auth.admin.create_user(user_data)
        
        # Now sign in to get the session tokens
        sign_in_result = client.auth.sign_in_with_password({"email": email, "password": password})
        
    except Exception as e:
        logger.warning("Signup failed — email=%s, error=%s", email, e)
        raise HTTPException(status_code=400, detail=str(e))

    if sign_in_result.user is None or sign_in_result.session is None:
        raise HTTPException(status_code=400, detail="Signup succeeded but auto-login failed")

    logger.info("User signed up and auto-confirmed — id=%s, email=%s", sign_in_result.user.id, email)

    return {
        "access_token": sign_in_result.session.access_token,
        "refresh_token": sign_in_result.session.refresh_token,
        "user_id": sign_in_result.user.id,
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


def get_google_oauth_url(redirect_to: str) -> str:
    client = get_anon_client()
    result = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": redirect_to},
    })
    return result.url


async def get_current_user(authorization: str = Header(...)) -> dict:
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
