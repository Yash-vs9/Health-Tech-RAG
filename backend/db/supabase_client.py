from __future__ import annotations

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache
def get_anon_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


@lru_cache
def get_admin_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
