"""FastAPI application entry point."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version as get_version

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config.settings import get_settings
from app.core.exceptions import APIError
from app.core.logging import setup_logging
from app.core.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    correlation_id_var,
)
from app.db.session import get_engine
from app.health.router import router as health_router
from app.items.router import router as items_router


def get_app_version() -> str:
    """Get application version from package metadata."""
    try:
        return get_version("my-project")
    except PackageNotFoundError:
        return "0.0.0-dev"


# OpenAPI tags for documentation
OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Health check endpoints for liveness and readiness probes",
    },
    {
        "name": "items",
        "description": "CRUD operations for items (requires API key authentication)",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    import logging

    from sqlalchemy import text

    from app.db.session import get_session_factory

    logger = logging.getLogger(__name__)

    # Startup
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Application starting up")

    # Verify database connectivity at startup
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connectivity verified")
    except Exception as e:
        logger.error("Database connectivity check failed: %s", e)
        raise RuntimeError("Cannot connect to database") from e

    yield

    # Shutdown
    logger.info("Application shutting down")
    try:
        await get_engine().dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error("Error disposing database engine: %s", e)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'"
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app: object, max_size: int) -> None:
        """Initialize with max request size in bytes."""
        super().__init__(app)  # type: ignore[arg-type]
        self.max_size = max_size

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Check request size before processing."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )
        return await call_next(request)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Disable OpenAPI docs in production (when debug=False)
    docs_url = "/docs" if settings.debug else None
    redoc_url = "/redoc" if settings.debug else None
    openapi_url = "/openapi.json" if settings.debug else None

    app = FastAPI(
        title=settings.app_name,
        version=get_app_version(),
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        openapi_tags=OPENAPI_TAGS,
    )

    # Add CORS middleware only if origins are configured
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-API-Key",
                "X-Correlation-ID",
            ],
            expose_headers=["X-Correlation-ID", "X-Process-Time"],
        )

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.max_request_size)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RequestLoggingMiddleware, expose_timing=settings.expose_timing_header
    )
    app.add_middleware(CorrelationIdMiddleware)

    # Register exception handlers
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle custom API errors with correlation ID for debugging."""
        correlation_id = correlation_id_var.get()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error": type(exc).__name__,
                "correlation_id": correlation_id,
                **exc.details,
            },
            headers={"X-Correlation-ID": correlation_id} if correlation_id else None,
        )

    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors with correlation ID."""
        correlation_id = correlation_id_var.get()
        # Convert errors to JSON-serializable format (ctx may contain non-serializable objects)
        errors = []
        for error in exc.errors():
            clean_error = {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "input": error.get("input"),
            }
            errors.append(clean_error)
        return JSONResponse(
            status_code=422,
            content={
                "detail": errors,
                "error": "ValidationError",
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id} if correlation_id else None,
        )

    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions with correlation ID for debugging."""
        import logging

        logger = logging.getLogger(__name__)
        correlation_id = correlation_id_var.get()
        logger.exception(
            "Unhandled exception",
            extra={"correlation_id": correlation_id, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": "InternalServerError",
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id} if correlation_id else None,
        )

    app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        validation_error_handler,  # pyright: ignore[reportArgumentType]
    )
    app.add_exception_handler(
        Exception,
        generic_exception_handler,  # pyright: ignore[reportArgumentType]
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(items_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint with welcome message."""
    settings = get_settings()
    if settings.debug:
        return {"message": "Welcome to the API. Visit /docs for documentation."}
    return {"message": "Welcome to the API."}


def main() -> None:
    """Run the application using uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
