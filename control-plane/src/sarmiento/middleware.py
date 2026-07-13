from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class MaxRequestBodyMiddleware:
    """Reject oversized request bodies before application parsing."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse(
                        {"detail": "Request body too large"}, status_code=413
                    )(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                    scope, receive, send
                )
                return

        buffered: list[Message] = []
        total = 0
        more = True
        while more:
            message = await receive()
            buffered.append(message)
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await JSONResponse({"detail": "Request body too large"}, status_code=413)(
                    scope, receive, send
                )
                return
            more = bool(message.get("more_body", False))

        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)
