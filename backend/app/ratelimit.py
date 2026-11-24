"""Minimal in-memory sliding-window rate limiter for public endpoints.

Single-process only (fine for this demo). For multiple instances use Redis (e.g. slowapi + Redis).
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import settings

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")  # set by the hosting proxy
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit(name: str, max_calls: int, per_seconds: int):
    """FastAPI dependency: allow `max_calls` per `per_seconds` per client IP, else HTTP 429."""

    def dep(request: Request) -> None:
        if settings.inline_jobs:  # test mode
            return
        key, now = (name, client_ip(request)), time.monotonic()
        with _lock:
            if len(_hits) > 20_000:  # crude memory bound
                _hits.clear()
            q = _hits[key]
            while q and now - q[0] > per_seconds:
                q.popleft()
            if len(q) >= max_calls:
                raise HTTPException(429, "Too many requests, please slow down", headers={"Retry-After": str(per_seconds)})
            q.append(now)

    return dep
