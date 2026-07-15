from __future__ import annotations

import os
from functools import lru_cache
from supabase import create_client, Client


# Module-level variables for testing override
_anon_client: Client | None = None
_admin_client: Client | None = None


def reset_clients():
    """Reset clients for testing."""
    global _anon_client, _admin_client
    _anon_client = None
    _admin_client = None


@lru_cache
def get_anon_client() -> Client:
    global _anon_client
    if _anon_client is not None:
        return _anon_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


@lru_cache
def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is not None:
        return _admin_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def set_anon_client(client: Client):
    """Set anon client for testing."""
    global _anon_client
    _anon_client = client


def set_admin_client(client: Client):
    """Set admin client for testing."""
    global _admin_client
    _admin_client = client
