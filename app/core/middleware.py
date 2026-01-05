"""Request middleware for logging and correlation IDs."""

import logging
import re
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Context variable for correlation ID - accessible throughout the request lifecycle
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Correlation ID validation: alphanumeric, hyphens, underscores only, max 64 chars
_CORRELATION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that manages correlation IDs for request tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Extract or generate correlation ID and add to response headers."""
        # Get correlation ID from request header or generate a new one
        client_correlation_id = request.headers.get("X-Correlation-ID")

        # Validate client-provided correlation ID to prevent log injection
        if client_correlation_id and _CORRELATION_ID_PATTERN.match(
            client_correlation_id
        ):
            correlation_id = client_correlation_id
        else:
            correlation_id = str(uuid4())

        correlation_id_var.set(correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request details and timing."""

    def __init__(
        self,
        app: ASGIApp,
        logger: logging.Logger | None = None,
        expose_timing: bool = True,
    ) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger("app.requests")
        self.expose_timing = expose_timing

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request details and processing time."""
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # Log request details
        self.logger.info(
            "Request completed | method=%s | path=%s | status=%d | time=%.2fms",
            request.method,
            request.url.path,
            response.status_code,
            process_time_ms,
        )

        # Add timing header only if configured (disable in production to prevent timing attacks)
        if self.expose_timing:
            response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
        return response
