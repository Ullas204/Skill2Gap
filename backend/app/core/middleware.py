import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        logger.info(
            "%s %s -> %d (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    _requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = settings.rate_limit_window_seconds
        max_requests = settings.rate_limit_requests

        timestamps = self._requests.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < window]

        if len(timestamps) >= max_requests:
            raise RateLimitError(detail="Too many requests")

        timestamps.append(now)
        self._requests[client_ip] = timestamps

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)
