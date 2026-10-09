"""In-memory TTL cache for hot short-code lookups.

This is a simple dict-backed cache with per-key expiration.
In a future phase it can be swapped out for Redis without changing
the interface used by callers.
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.config import settings


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class InMemoryCache:
    """Thread-safe, size-bounded, TTL-based cache."""

    def __init__(
        self,
        ttl: int = settings.CACHE_TTL,
        max_size: int = settings.CACHE_MAX_SIZE,
    ) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = Lock()

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Return cached value or *None* if missing / expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value. Evicts the oldest entry if at capacity."""
        with self._lock:
            if len(self._store) >= self._max_size and key not in self._store:
                self._evict_one()
            self._store[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + (ttl or self._ttl),
            )

    def delete(self, key: str) -> None:
        """Remove a key (no-op if absent)."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Flush every entry."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)

    # ── Internals ─────────────────────────────────────────────────────────

    def _evict_one(self) -> None:
        """Remove the entry with the earliest expiration."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
        del self._store[oldest_key]


# Module-level singleton used across the application.
cache = InMemoryCache()
