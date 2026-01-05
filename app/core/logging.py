"""Logging configuration with correlation ID support."""

import logging
import sys
from typing import Any

from app.core.middleware import correlation_id_var


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to the log record."""
        record.correlation_id = correlation_id_var.get("")
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging with correlation ID support.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    # Create formatter with correlation ID
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: The logger name (typically __name__).

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    # Ensure the correlation ID filter is added
    if not any(isinstance(f, CorrelationIdFilter) for f in logger.filters):
        logger.addFilter(CorrelationIdFilter())
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context.

    Args:
        logger: The logger to use.
        level: The logging level.
        message: The log message.
        **context: Additional context to include in the log.
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} | {context_str}"
    logger.log(level, message)
