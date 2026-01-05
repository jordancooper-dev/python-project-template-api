"""Application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Validation constants
BCRYPT_ROUNDS_MIN = 10  # Security minimum
BCRYPT_ROUNDS_MAX = 16  # Performance limit
POOL_TIMEOUT_MIN = 1  # Minimum 1 second
POOL_TIMEOUT_MAX = 300  # Maximum 5 minutes
STATEMENT_TIMEOUT_MIN = 1000  # Minimum 1 second (in ms)
STATEMENT_TIMEOUT_MAX = 300000  # Maximum 5 minutes (in ms)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "my-project"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    # API Key settings
    api_key_min_length: int = 32
    bcrypt_rounds: int = 12  # Bcrypt work factor (12-14 recommended for 2024+)

    # CORS settings
    # Empty = no CORS; use specific origins like ["https://example.com"]
    # WARNING: Do not use ["*"] with allow_credentials=True (browsers reject this)
    cors_origins: list[str] = []

    # Request size limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB default

    # Timing/debug headers (disable in production to prevent timing attacks)
    expose_timing_header: bool = True

    # Database timeouts
    database_pool_timeout: int = 30  # Connection pool timeout in seconds
    database_statement_timeout: int = 30000  # Statement timeout in milliseconds

    @field_validator("bcrypt_rounds")
    @classmethod
    def validate_bcrypt_rounds(cls, v: int) -> int:
        """Validate bcrypt rounds is within reasonable bounds."""
        if v < BCRYPT_ROUNDS_MIN:
            msg = (
                f"bcrypt_rounds must be at least {BCRYPT_ROUNDS_MIN} (security minimum)"
            )
            raise ValueError(msg)
        if v > BCRYPT_ROUNDS_MAX:
            msg = (
                f"bcrypt_rounds must be at most {BCRYPT_ROUNDS_MAX} (performance limit)"
            )
            raise ValueError(msg)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            msg = f"Invalid log level: {v}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return upper_v

    @field_validator("database_pool_timeout")
    @classmethod
    def validate_pool_timeout(cls, v: int) -> int:
        """Validate database pool timeout is within reasonable bounds."""
        if v < POOL_TIMEOUT_MIN:
            msg = f"database_pool_timeout must be at least {POOL_TIMEOUT_MIN} second"
            raise ValueError(msg)
        if v > POOL_TIMEOUT_MAX:
            msg = f"database_pool_timeout must be at most {POOL_TIMEOUT_MAX} seconds"
            raise ValueError(msg)
        return v

    @field_validator("database_statement_timeout")
    @classmethod
    def validate_statement_timeout(cls, v: int) -> int:
        """Validate database statement timeout is within reasonable bounds."""
        if v < STATEMENT_TIMEOUT_MIN:
            msg = f"database_statement_timeout must be at least {STATEMENT_TIMEOUT_MIN}ms (1 second)"
            raise ValueError(msg)
        if v > STATEMENT_TIMEOUT_MAX:
            msg = f"database_statement_timeout must be at most {STATEMENT_TIMEOUT_MAX}ms (5 minutes)"
            raise ValueError(msg)
        return v

    @property
    def async_database_url(self) -> str:
        """Get async database URL for psycopg3."""
        url = str(self.database_url)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
