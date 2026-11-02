"""Tiny thread-safe response cache, persisted to a JSON file.

Why: the biggest latency win is not calling the LLM at all for repeated
requests. Pre-warming this cache (see backend/prewarm.py) makes the expo demo
topics return instantly - even with no internet.
"""
import hashlib
import json
import os
import threading
import time
from typing import Any, Optional

from app.config import settings

_lock = threading.Lock()
_store: dict = {}
_loaded = False


def _load():
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        if os.path.exists(settings.CACHE_FILE):
            with open(settings.CACHE_FILE, "r", encoding="utf-8") as f:
                _store.update(json.load(f))
    except Exception:
        pass


def _persist():
    try:
        os.makedirs(os.path.dirname(settings.CACHE_FILE), exist_ok=True)
        tmp = settings.CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_store, f)
        os.replace(tmp, settings.CACHE_FILE)
    except Exception:
        pass


def make_key(kind: str, *parts: Any) -> str:
    raw = "|".join(str(p).strip().lower() for p in parts)
    return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()}"


def get(key: str) -> Optional[Any]:
    with _lock:
        _load()
        item = _store.get(key)
        if not item:
            return None
        if time.time() - item["t"] > settings.CACHE_TTL_SECONDS:
            _store.pop(key, None)
            return None
        return item["v"]


def set(key: str, value: Any) -> None:
    with _lock:
        _load()
        _store[key] = {"t": time.time(), "v": value}
        _persist()
