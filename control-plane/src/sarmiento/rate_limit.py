from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SlidingWindowRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, default_per_minute: int, login_per_minute: int) -> None:
        super().__init__(app)
        self.default_limit = default_per_minute
        self.login_limit = login_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/healthz", "/readyz"} or not path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        bucket = "login" if path == "/api/v1/auth/login" else "api"
        limit = self.login_limit if bucket == "login" else self.default_limit
        key = f"{client}:{bucket}"
        now = time.monotonic()
        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= limit:
                retry_after = max(1, int(60 - (now - queue[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
            queue.append(now)
        return await call_next(request)
