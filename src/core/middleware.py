"""
DPOS Middleware Module
Request/response middleware for logging, rate limiting, and request validation.
"""
import time
import uuid
from datetime import datetime, UTC
from typing import Callable, Dict, Optional
from collections import defaultdict
import asyncio

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.logging import (
    get_logger,
    set_request_context,
    get_correlation_id,
    correlation_id_var
)

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        # Set context for logging
        set_request_context(
            correlation_id=correlation_id,
            request_id=request_id
        )

        # Store in request state for access in routes
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    Limits requests per IP address.
    """

    def __init__(self, app, requests_per_minute: int = 100, burst: int = 20):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.window_size = 60  # seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        async with self._lock:
            # Clean old requests outside window
            self._requests[client_ip] = [
                req_time for req_time in self._requests[client_ip]
                if current_time - req_time < self.window_size
            ]

            # Check rate limit
            request_count = len(self._requests[client_ip])

            if request_count >= self.requests_per_minute:
                retry_after = int(self.window_size - (current_time - self._requests[client_ip][0]))
                logger.warning(
                    f"Rate limit exceeded for {client_ip}",
                    extra={
                        "client_ip": client_ip,
                        "request_count": request_count,
                        "limit": self.requests_per_minute
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(current_time) + retry_after)
                    }
                )

            # Record this request
            self._requests[client_ip].append(current_time)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - len(self._requests[client_ip]))
        )

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and sanitization."""

    MAX_CONTENT_LENGTH = settings.max_upload_size_bytes
    MAX_QUERY_LENGTH = 2000
    MAX_HEADER_SIZE = 8192

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.MAX_CONTENT_LENGTH:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Request body too large. Maximum size: {settings.max_upload_size_mb}MB"
                        }
                    )
            except ValueError:
                pass

        # Validate query string length
        if len(str(request.query_params)) > self.MAX_QUERY_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_414_URI_TOO_LONG,
                content={"detail": "Query string too long"}
            )

        # Validate headers
        total_header_size = sum(
            len(k) + len(v) for k, v in request.headers.items()
        )
        if total_header_size > self.MAX_HEADER_SIZE:
            return JSONResponse(
                status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                content={"detail": "Request headers too large"}
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only add HSTS in production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (adjust as needed)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            # Allow inline scripts for Swagger UI
            pass
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(
                f"Unhandled exception: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(e).__name__
                }
            )

            # In production, don't expose internal error details
            if settings.is_production:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "detail": "Internal server error",
                        "correlation_id": get_correlation_id()
                    }
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "detail": str(e),
                        "error_type": type(e).__name__,
                        "correlation_id": get_correlation_id()
                    }
                )
