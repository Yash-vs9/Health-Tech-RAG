"""
Supabase client factory.

Provides two singleton clients:
    - anon_client: Uses SUPABASE_ANON_KEY, safe for frontend-facing operations
    - admin_client: Uses SUPABASE_SERVICE_ROLE_KEY, bypasses RLS (backend only)

Both are cached via @lru_cache to avoid repeated initialization.

Env vars used:
    SUPABASE_URL               - Project URL (required)
    SUPABASE_ANON_KEY          - Anonymous/public key (required)
    SUPABASE_SERVICE_ROLE_KEY  - Service role key, backend only (required)

Usage:
    from backend.db.supabase_client import get_admin_client
    client = get_admin_client()
    result = client.table("chat_sessions").select("*").execute()
"""

from __future__ import annotations

import os
from supabase import create_client, Client


_anon_client: Client | None = None
_admin_client: Client | None = None


def reset_clients():
    global _anon_client, _admin_client
    _anon_client = None
    _admin_client = None


def get_anon_client() -> Client:
    global _anon_client
    if _anon_client is not None:
        return _anon_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    _anon_client = create_client(url, key)
    return _anon_client


def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is not None:
        return _admin_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    _admin_client = create_client(url, key)
    return _admin_client


def set_anon_client(client: Client):
    global _anon_client
    _anon_client = client


def set_admin_client(client: Client):
    global _admin_client
    _admin_client = client
