"""
Supabase client setup.

Two clients are exposed:
- supabase_anon: uses the anon key, respects Row Level Security (RLS).
                  Used for auth operations (signup/login) where the user
                  isn't authenticated yet.
- supabase_admin: uses the service_role key, BYPASSES RLS.
                  Used by the backend for trusted server-side operations
                  (e.g. verifying a JWT, looking up a profile by id).

NEVER expose supabase_admin's key to the frontend.
"""
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
