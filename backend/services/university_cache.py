from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional

import requests


@dataclass
class CacheEntry:
    value: Any
    created_at: datetime
    expires_at: datetime


class UniversityCache:
    def __init__(self, ttl_seconds: int = 24 * 60 * 60):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _make_entry(self, value: Any, ttl_seconds: Optional[int] = None) -> CacheEntry:
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        created_at = self._now()
        return CacheEntry(value=value, created_at=created_at, expires_at=created_at + timedelta(seconds=ttl))

    def _is_expired(self, entry: CacheEntry) -> bool:
        return self._now() >= entry.expires_at

    def prune(self) -> None:
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if self._is_expired(entry)]
            for key in expired_keys:
                self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if self._is_expired(entry):
                self._cache.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> Any:
        with self._lock:
            self._cache[key] = self._make_entry(value, ttl_seconds)
        return value

    def fetch_text(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        ttl_seconds: Optional[int] = None,
        cache_key: Optional[str] = None,
    ) -> str:
        key = cache_key or f"text:{url}:{sorted((params or {}).items())}"
        cached = self.get(key)
        if cached is not None:
            return cached

        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        text = response.text
        self.set(key, text, ttl_seconds=ttl_seconds)
        return text

    def fetch_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        ttl_seconds: Optional[int] = None,
        cache_key: Optional[str] = None,
    ) -> Any:
        key = cache_key or f"json:{url}:{sorted((params or {}).items())}"
        cached = self.get(key)
        if cached is not None:
            return cached

        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        self.set(key, payload, ttl_seconds=ttl_seconds)
        return payload
