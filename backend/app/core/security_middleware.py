"""Security middleware — audit logging, request validation, security headers."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    _SENSITIVE_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        if request.url.path in self._SENSITIVE_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                "Security: %s %s -> %d (%.3fs) ip=%s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
                client_ip,
            )
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    _MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self._MAX_BODY_SIZE:
            return Response(
                content='{"detail":"Request body too large","code":"payload_too_large"}',
                status_code=413,
                media_type="application/json",
            )

        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.body()
                if b"\x00" in body:
                    return Response(
                        content='{"detail":"Invalid request body","code":"invalid_body"}',
                        status_code=400,
                        media_type="application/json",
                    )

        return await call_next(request)


def register_security_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditLoggingMiddleware)
    app.add_middleware(InputSanitizationMiddleware)
