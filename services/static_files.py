from fastapi.staticfiles import StaticFiles
from starlette.types import Scope, Receive, Send
from typing import Any


class CachedStaticFiles(StaticFiles):
    def __init__(self, *args: Any, cache_seconds: int = 3600, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cache_seconds = max(0, int(cache_seconds))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                headers = message.setdefault("headers", [])
                # Add simple Cache-Control for static assets
                headers.append((b"cache-control", f"public, max-age={self._cache_seconds}".encode("ascii")))
            await send(message)

        await super().__call__(scope, receive, send_wrapper)

