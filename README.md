# FastAPI Project Template

A production-ready FastAPI template with PostgreSQL, async SQLAlchemy, API key authentication, and comprehensive tooling.

## Features

### Core

- **FastAPI** - Modern async Python web framework
- **PostgreSQL + psycopg3** - Async PostgreSQL driver
- **SQLAlchemy 2.0** - Async ORM with type hints
- **Alembic** - Database migrations
- **Pydantic Settings** - Type-safe configuration
- **Typer CLI** - Command-line interface for key management

### Security

- **API Key Authentication** - Secure, database-stored API keys with bcrypt hashing and optional expiration
- **Configurable Bcrypt Rounds** - Tunable work factor (10-16) for security vs performance tradeoff
- **Security Headers** - CSP, X-Frame-Options, X-Content-Type-Options, etc.
- **CORS** - Configurable Cross-Origin Resource Sharing (with credentials warning)
- **Request Size Limits** - Configurable maximum request body size
- **Input Validation** - Pydantic validation with whitespace handling
- **SQL Injection Prevention** - Parameterized queries throughout
- **Timing Attack Prevention** - Configurable process time header (disable in production)

### Observability

- **Health Checks** - Liveness and readiness probes (Kubernetes-compatible) with query timeout
- **Correlation IDs** - Request tracing across logs and error responses
- **Structured Logging** - JSON-formatted logs with context
- **Process Time Headers** - Request duration tracking (configurable)
- **Startup Connectivity Check** - Database verification on application startup
- **Generic Exception Handler** - Unhandled errors include correlation ID for debugging

### Developer Experience

- **Docker** - Production-ready multi-stage Dockerfile
- **uv** - Fast Python package manager
- **Ruff + mypy + Pyright** - Comprehensive linting and type checking
- **pytest** - Testing with async support and coverage reporting
- **Pre-commit Hooks** - Automated code quality checks

## Project Structure

```text
project-root/
├── app/
│   ├── auth/                   # API key authentication
│   │   ├── dependencies.py     # FastAPI auth dependencies
│   │   ├── models.py           # APIKey SQLAlchemy model
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── service.py          # Key management logic
│   ├── cli/                    # CLI commands
│   │   ├── __init__.py         # Typer app setup
│   │   └── keys.py             # API key management commands
│   ├── config/
│   │   └── settings.py         # Pydantic Settings
│   ├── core/
│   │   ├── exceptions.py       # Custom exception classes
│   │   ├── logging.py          # Structured logging
│   │   └── middleware.py       # Correlation ID, request logging
│   ├── db/
│   │   ├── base.py             # SQLAlchemy base class with UTC timestamps
│   │   └── session.py          # Async session management
│   ├── health/
│   │   ├── router.py           # Health check endpoints
│   │   └── schemas.py          # Health response schemas
│   ├── items/                  # Example CRUD domain
│   │   ├── models.py           # Item model
│   │   ├── router.py           # Item endpoints
│   │   ├── schemas.py          # Item schemas
│   │   └── service.py          # Item CRUD operations
│   └── main.py                 # FastAPI application
├── alembic/
│   ├── env.py                  # Async migration environment
│   └── versions/               # Migration files
├── tests/
│   ├── factories/              # Test data factories
│   ├── conftest.py             # Pytest fixtures
│   └── test_*.py               # Test files
├── .env.example                # Environment variable template
├── alembic.ini                 # Alembic configuration
├── Dockerfile                  # Production Docker image
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd <project-name>
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Set Up Database

```bash
# Start PostgreSQL (example with Docker)
docker run -d --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=myproject \
  -p 5432:5432 \
  postgres:16

# Run migrations
uv run alembic upgrade head
```

### 4. Create an API Key

```bash
uv run my-project keys create --name "My App" --client-id "app-1"
# Save the displayed key - it's only shown once!
```

### 5. Start the Server

```bash
uv run my-project serve
# Or for development with auto-reload:
uv run my-project serve --reload
```

### 6. Test the API

```bash
# Health check (no auth required)
curl http://localhost:8000/health/live

# Create an item (auth required)
curl -X POST http://localhost:8000/api/v1/items \
  -H "X-API-Key: sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "A test item"}'

# List items
curl http://localhost:8000/api/v1/items \
  -H "X-API-Key: sk_your_key_here"
```

## CLI Commands

### Server

```bash
my-project serve              # Start API server
my-project serve --reload     # Start with auto-reload
my-project serve --port 3000  # Custom port
my-project version            # Show version
```

### API Key Management

```bash
# Create a new key
my-project keys create --name "Production App" --client-id "prod-001"

# List all keys
my-project keys list

# Show key details
my-project keys info sk_abc123

# Revoke a key
my-project keys revoke sk_abc123
```

## API Endpoints

### Health Checks

| Endpoint        | Method | Auth | Description                     |
| --------------- | ------ | ---- | ------------------------------- |
| `/health/live`  | GET    | No   | Liveness probe                  |
| `/health/ready` | GET    | No   | Readiness probe (checks DB)     |

### Items (Example CRUD)

| Endpoint              | Method | Auth | Description        |
| --------------------- | ------ | ---- | ------------------ |
| `/api/v1/items`       | POST   | Yes  | Create item        |
| `/api/v1/items`       | GET    | Yes  | List items         |
| `/api/v1/items/{id}`  | GET    | Yes  | Get item           |
| `/api/v1/items/{id}`  | PATCH  | Yes  | Update item        |
| `/api/v1/items/{id}`  | DELETE | Yes  | Delete item        |

### Documentation

> **Note:** API documentation is only available in debug mode (`DEBUG=true`).

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Configuration

All settings are loaded from environment variables:

### Application Settings

| Variable    | Default    | Description                              |
| ----------- | ---------- | ---------------------------------------- |
| `APP_NAME`  | my-project | Application name                         |
| `DEBUG`     | false      | Enable debug mode (enables API docs)     |
| `LOG_LEVEL` | INFO       | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Database Settings

| Variable                     | Default   | Description                          |
| ---------------------------- | --------- | ------------------------------------ |
| `DATABASE_URL`               | (required)| PostgreSQL connection URL            |
| `DATABASE_POOL_SIZE`         | 5         | Connection pool size                 |
| `DATABASE_MAX_OVERFLOW`      | 10        | Max overflow connections             |
| `DATABASE_ECHO`              | false     | Log SQL queries                      |
| `DATABASE_POOL_TIMEOUT`      | 30        | Pool timeout in seconds (1-300)      |
| `DATABASE_STATEMENT_TIMEOUT` | 30000     | Query timeout in ms (1000-300000)    |

### Security Settings

| Variable               | Default   | Description                                    |
| ---------------------- | --------- | ---------------------------------------------- |
| `API_KEY_MIN_LENGTH`   | 32        | Minimum key length                             |
| `BCRYPT_ROUNDS`        | 12        | Bcrypt work factor (10-16, higher = slower)    |
| `CORS_ORIGINS`         | []        | Allowed CORS origins (JSON array)              |
| `MAX_REQUEST_SIZE`     | 10485760  | Max request body size in bytes                 |
| `EXPOSE_TIMING_HEADER` | true      | Expose X-Process-Time header (disable in prod) |

## Security Features

### API Key Authentication

- Keys are generated with `secrets.token_urlsafe(32)`
- Only bcrypt hashes are stored in the database (configurable work factor)
- Key prefix (first 12 chars) stored with unique constraint for O(1) lookups
- Atomic key validation with row-level locking (SELECT FOR UPDATE)
- Unified error messages prevent user enumeration
- Last-used timestamp tracking
- Optional key expiration with automatic validation
- Correlation ID included in all auth failure logs

### Request Security

- **Content-Security-Policy** - Strict CSP without unsafe-inline
- **X-Frame-Options: DENY** - Prevents clickjacking
- **X-Content-Type-Options: nosniff** - Prevents MIME sniffing
- **X-XSS-Protection: 1; mode=block** - XSS filter
- **Referrer-Policy: strict-origin-when-cross-origin**
- **Request size limits** - Configurable with Content-Length validation
- **CORS** - Explicit methods/headers (not wildcards)

### Input Validation

- Pydantic validation with whitespace handling
- Correlation ID validation (alphanumeric, max 64 chars) prevents log injection
- Pagination bounds (skip: 0-1000, limit: 1-100)
- Content-Length header parsing with error handling

### Database Security

- Parameterized queries (SQL injection prevention)
- Statement timeout to prevent long-running queries
- Connection pool timeout configuration
- Health check query timeout (5 seconds)
- UTC timestamps for consistency
- Row-level locking for concurrent updates

### Error Handling

- Graceful engine disposal on shutdown
- Structured error logging with correlation IDs
- Unified authentication error messages
- Generic exception handler returns correlation ID for debugging
- Startup database connectivity verification

## Development

### Run Tests

```bash
uv run pytest                 # Run all tests
uv run pytest -v              # Verbose output
uv run pytest --no-cov        # Skip coverage (faster)
```

### Run Linting

```bash
uv run ruff check .           # Lint
uv run ruff check --fix .     # Lint and auto-fix
uv run ruff format .          # Format code
```

### Run Type Checking

```bash
uv run mypy app               # mypy
uv run pyright                # Pyright
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Add new table"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

### Pre-commit Hooks

```bash
uv run pre-commit install              # Install hooks
uv run pre-commit run --all-files      # Run manually
```

## Docker

### Build and Run

```bash
# Build image
docker build -t my-project .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  my-project
```

### Production Considerations

- Set `DEBUG=false` to disable API documentation endpoints
- Configure `CORS_ORIGINS` appropriately for your domain
- Use secrets management for `DATABASE_URL`
- Set appropriate `MAX_REQUEST_SIZE` for your use case
- Configure database timeouts for your workload

## Customization

### Renaming the Project

This template uses `my-project` as the default project name. To rename it for your use:

1. **Update `pyproject.toml`** - Change the project name and CLI command:

   ```toml
   [project]
   name = "your-project-name"

   [project.scripts]
   your-project-name = "app.cli:app"
   ```

2. **Update `app/config/settings.py`** - Change the default app name:

   ```python
   app_name: str = "your-project-name"
   ```

3. **Update `app/main.py`** - Change the package name in `get_app_version()`:

   ```python
   def get_app_version() -> str:
       try:
           return get_version("your-project-name")  # Change this
       except PackageNotFoundError:
           return "0.0.0-dev"
   ```

4. **Reinstall the package**:

   ```bash
   uv sync
   ```

After renaming, your CLI commands will use the new name:

```bash
your-project-name serve
your-project-name keys create --name "My Key" --client-id "app-1"
```

### Adding a New Domain

1. Create a new directory: `app/your_domain/`
2. Add files: `models.py`, `schemas.py`, `service.py`, `router.py`
3. Import and register the router in `app/main.py`
4. Create a migration: `uv run alembic revision --autogenerate -m "Add your_domain"`

### Changing Authentication

The API key authentication can be customized in `app/auth/`:

- `dependencies.py` - Modify the `get_api_key` function
- `service.py` - Add scopes, permissions, or rate limiting
- `models.py` - Add fields like `scopes` (expiration is already built-in)

## Transaction Patterns

The application provides two database session dependencies:

### Auto-commit (default)

```python
@router.post("/items")
async def create_item(
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ItemCreate,
) -> ItemResponse:
    item = Item(**data.model_dump())
    db.add(item)
    # Commit happens automatically after endpoint returns
    return ItemResponse.model_validate(item)
```

### Manual transaction control

```python
@router.post("/batch")
async def batch_operation(
    db: Annotated[AsyncSession, Depends(get_db_no_commit)],
) -> dict:
    for batch in batches:
        for item in batch:
            db.add(item)
        await db.commit()  # Explicit commit per batch
    return {"status": "ok"}
```

## License

MIT
