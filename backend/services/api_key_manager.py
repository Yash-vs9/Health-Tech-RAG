from __future__ import annotations

import os
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from backend.logging_config import get_logger

logger = get_logger("backend.api_key_manager")


@dataclass
class KeyState:
    """Tracks state for a single API key."""
    key: str
    last_used: float = 0.0
    failure_count: int = 0
    last_failure: float = 0.0
    cooldown_until: float = 0.0
    total_requests: int = 0
    total_failures: int = 0


class APIKeyManager:
    """
    Load balances across multiple API keys with retry and cooldown logic.

    Supports round-robin rotation with automatic cooldown on rate limit errors.
    When a key hits a rate limit (429), it's put into cooldown and the next key
    is used. After cooldown expires, the key becomes available again.
    """

    # Default cooldown after a rate limit error (seconds)
    DEFAULT_COOLDOWN = 60.0
    # Max consecutive failures before permanent cooldown for longer period
    MAX_FAILURES = 5
    # Extended cooldown after max failures
    EXTENDED_COOLDOWN = 300.0

    def __init__(
        self,
        keys: list[str],
        provider_name: str = "default",
        cooldown: float | None = None,
    ):
        if not keys:
            raise ValueError(f"No API keys provided for {provider_name}")

        self.provider_name = provider_name
        self.cooldown = cooldown or self.DEFAULT_COOLDOWN
        self._lock = threading.Lock()
        self._index = 0

        self._keys = [
            KeyState(key=k) for k in keys
        ]

        logger.info(
            "API key manager initialized — provider=%s, keys=%d",
            provider_name, len(self._keys),
        )

    def get_key(self) -> str:
        """Get the next available API key using round-robin with cooldown awareness."""
        with self._lock:
            now = time.time()
            n = len(self._keys)

            # Try to find a key that's not in cooldown
            for _ in range(n):
                ks = self._keys[self._index % n]
                self._index += 1

                if ks.cooldown_until > now:
                    # Key is in cooldown, skip it
                    remaining = int(ks.cooldown_until - now)
                    logger.debug(
                        "Key %s... in cooldown (%ds remaining), skipping",
                        ks.key[:8], remaining,
                    )
                    continue

                ks.last_used = now
                ks.total_requests += 1
                logger.debug(
                    "Using key %s... (provider=%s, request #%d)",
                    ks.key[:8], self.provider_name, ks.total_requests,
                )
                return ks.key

            # All keys in cooldown — return the one that expires soonest
            soonest = min(self._keys, key=lambda k: k.cooldown_until)
            remaining = int(soonest.cooldown_until - now)
            logger.warning(
                "All %d keys for %s in cooldown. Using soonest (%ds remaining)",
                n, self.provider_name, remaining,
            )
            soonest.last_used = now
            soonest.total_requests += 1
            return soonest.key

    def report_success(self, key: str) -> None:
        """Report a successful use of the key (resets failure count)."""
        with self._lock:
            for ks in self._keys:
                if ks.key == key:
                    ks.failure_count = 0
                    break

    def report_rate_limit(self, key: str) -> None:
        """Report a 429 rate limit error — puts key into cooldown."""
        with self._lock:
            now = time.time()
            for ks in self._keys:
                if ks.key == key:
                    ks.failure_count += 1
                    ks.total_failures += 1
                    ks.last_failure = now

                    if ks.failure_count >= self.MAX_FAILURES:
                        cd = self.EXTENDED_COOLDOWN
                        logger.warning(
                            "Key %s... hit %d failures — extended cooldown %ds",
                            ks.key[:8], ks.failure_count, cd,
                        )
                    else:
                        cd = self.cooldown

                    ks.cooldown_until = now + cd
                    logger.info(
                        "Key %s... rate limited — cooldown %ds (failures=%d)",
                        ks.key[:8], int(cd), ks.failure_count,
                    )
                    break

    def report_error(self, key: str, error: Exception) -> None:
        """Report a transient error (may or may not be rate limit related)."""
        err_str = str(error).lower()
        if "429" in err_str or "rate limit" in err_str or "too many" in err_str:
            self.report_rate_limit(key)
        elif "401" in err_str or "403" in err_str or "unauthorized" in err_str:
            logger.error("Auth error with key %s...: %s", key[:8], error)
        else:
            logger.debug("Non-rate-limit error with key %s...: %s", key[:8], error)

    def get_stats(self) -> dict:
        """Return usage statistics for all keys."""
        with self._lock:
            now = time.time()
            return {
                self.provider_name: {
                    "total_keys": len(self._keys),
                    "active_keys": sum(
                        1 for ks in self._keys if ks.cooldown_until <= now
                    ),
                    "keys": [
                        {
                            "key_prefix": ks.key[:8] + "...",
                            "total_requests": ks.total_requests,
                            "total_failures": ks.total_failures,
                            "in_cooldown": ks.cooldown_until > now,
                            "cooldown_remaining": max(0, int(ks.cooldown_until - now)),
                        }
                        for ks in self._keys
                    ],
                }
            }


def load_keys_from_env(env_var: str, separator: str = ",") -> list[str]:
    """
    Load API keys from an environment variable.
    
    Supports formats:
      - Single key: "nvapi-xxx"
      - Comma-separated: "nvapi-xxx,nvapi-yyy"
      - Newline-separated: "nvapi-xxx\nnvapi-yyy"
    
    Returns a list of non-empty, stripped keys.
    """
    raw = os.getenv(env_var, "")
    if not raw:
        return []

    # Handle both comma and newline separators
    keys = []
    for part in raw.replace("\n", separator).split(separator):
        k = part.strip().strip('"').strip("'")
        if k:
            keys.append(k)

    return keys


# ── Singleton instances ──────────────────────────────────────────────────

_nvidia_manager: APIKeyManager | None = None
_hf_manager: APIKeyManager | None = None
_lock = threading.Lock()


def get_nvidia_key_manager() -> APIKeyManager:
    """Get or create the NVIDIA API key manager singleton."""
    global _nvidia_manager
    if _nvidia_manager is not None:
        return _nvidia_manager

    with _lock:
        if _nvidia_manager is not None:
            return _nvidia_manager

        keys = load_keys_from_env("NVIDIA_API_KEYS")
        if not keys:
            # Fallback to single key
            single = os.getenv("NVIDIA_API_KEY", "")
            if single:
                keys = [single]

        if not keys:
            raise ValueError(
                "No NVIDIA API keys found. Set NVIDIA_API_KEYS (comma-separated) "
                "or NVIDIA_API_KEY in your .env file."
            )

        _nvidia_manager = APIKeyManager(
            keys=keys,
            provider_name="nvidia",
            cooldown=float(os.getenv("NVIDIA_KEY_COOLDOWN", "60")),
        )
        return _nvidia_manager


def get_hf_key_manager() -> APIKeyManager:
    """Get or create the HuggingFace API key manager singleton."""
    global _hf_manager
    if _hf_manager is not None:
        return _hf_manager

    with _lock:
        if _hf_manager is not None:
            return _hf_manager

        keys = load_keys_from_env("HF_API_KEYS")
        if not keys:
            # Fallback to single key
            single = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
            if single:
                keys = [single]

        if not keys:
            raise ValueError(
                "No HuggingFace API keys found. Set HF_API_KEYS (comma-separated) "
                "or HUGGINGFACEHUB_API_TOKEN in your .env file."
            )

        _hf_manager = APIKeyManager(
            keys=keys,
            provider_name="huggingface",
            cooldown=float(os.getenv("HF_KEY_COOLDOWN", "60")),
        )
        return _hf_manager
