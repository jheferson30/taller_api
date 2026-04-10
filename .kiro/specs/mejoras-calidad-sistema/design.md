# Design Document: System Quality Improvements

## Overview

This design document details the technical implementation for 9 non-critical quality, maintainability, and production-readiness improvements identified in the system audit. These improvements enhance security posture, developer experience, code quality, and operational readiness without modifying core business logic.

The improvements are organized into three categories:
- **Infrastructure & Operations**: Secrets management, Docker containerization, database migrations
- **Security & Validation**: Input sanitization, HTTP compression, async processing
- **Code Quality & Documentation**: Type hints, linting, API documentation

### Scope

This design covers:
- Azure Key Vault integration for secrets management
- Complete Docker setup with multi-stage builds
- Alembic migration framework configuration
- Input validation with bleach and file upload validators
- GZip compression middleware
- Celery + Redis for async PDF generation
- Complete type hints with mypy validation
- Ruff linter configuration with pre-commit hooks
- Enhanced OpenAPI documentation with examples

### Out of Scope

- Critical security fixes (handled in correcciones-auditoria-sistema spec)
- Frontend/mobile testing (separate spec)
- Performance optimization beyond compression
- Microservices architecture migration

## Architecture

### Current System Architecture


```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ React Web    │  │ React Native │  │  External    │     │
│  │   (Vite)     │  │    (Expo)    │  │   Clients    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │      FastAPI Application            │
          │  ┌────────────────────────────────┐ │
          │  │   Middleware Stack             │ │
          │  │  - CORS                        │ │
          │  │  - Auth                        │ │
          │  │  - Rate Limiting               │ │
          │  │  - GZip (NEW)                  │ │
          │  └────────────────────────────────┘ │
          │  ┌────────────────────────────────┐ │
          │  │   Routes Layer                 │ │
          │  └────────┬───────────────────────┘ │
          │  ┌────────▼───────────────────────┐ │
          │  │   Services Layer               │ │
          │  └────────┬───────────────────────┘ │
          │  ┌────────▼───────────────────────┐ │
          │  │   Repositories Layer           │ │
          │  └────────┬───────────────────────┘ │
          └───────────┼─────────────────────────┘
                      │
          ┌───────────▼─────────────────────────┐
          │      PostgreSQL Database            │
          │  (Managed by Alembic - NEW)         │
          └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              New Components (This Spec)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Azure Key    │  │    Celery    │  │    Redis     │     │
│  │   Vault      │  │   Workers    │  │   Broker     │     │
│  │  (Secrets)   │  │  (Async PDF) │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### New Architecture Components


1. **Azure Key Vault**: Centralized secrets management replacing plain-text .env variables
2. **Celery + Redis**: Distributed task queue for async PDF generation
3. **Alembic**: Database migration management with version control
4. **Input Sanitizer**: HTML sanitization and file validation layer
5. **GZip Middleware**: HTTP response compression
6. **Type Checking**: mypy static type analysis
7. **Linting**: Ruff for code quality enforcement
8. **Enhanced OpenAPI**: Comprehensive API documentation

### Technology Stack Additions

- **azure-identity** + **azure-keyvault-secrets**: Azure SDK for secrets management
- **celery[redis]**: Distributed task queue
- **redis**: In-memory data store (Celery broker)
- **alembic**: Database migration tool
- **bleach**: HTML sanitization library
- **python-magic**: MIME type detection
- **mypy**: Static type checker
- **ruff**: Fast Python linter and formatter

## Components and Interfaces

### 1. Secrets Manager Component

**Purpose**: Securely retrieve secrets from Azure Key Vault instead of plain-text environment variables.

**File**: `app/configuracion/secrets_manager.py`


```python
from typing import Optional
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
import os

class SecretsManager:
    """
    Manages secrets retrieval from Azure Key Vault with fallback to environment variables.
    
    Usage:
        secrets = SecretsManager()
        db_password = secrets.get_secret("database-password")
    """
    
    def __init__(self):
        self.vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        self.use_key_vault = self.vault_url is not None
        
        if self.use_key_vault:
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
        else:
            self.client = None
    
    def get_secret(self, secret_name: str, fallback_env_var: Optional[str] = None) -> str:
        """
        Retrieve secret from Key Vault or fallback to environment variable.
        
        Args:
            secret_name: Name of secret in Key Vault (e.g., "admin-password")
            fallback_env_var: Environment variable name to use if Key Vault unavailable
        
        Returns:
            Secret value as string
        
        Raises:
            RuntimeError: If secret not found in either location
        """
        if self.use_key_vault:
            try:
                secret = self.client.get_secret(secret_name)
                return secret.value
            except ResourceNotFoundError:
                if fallback_env_var:
                    value = os.getenv(fallback_env_var)
                    if value:
                        return value
                raise RuntimeError(f"Secret '{secret_name}' not found in Key Vault")
        
        # Fallback to environment variable
        if fallback_env_var:
            value = os.getenv(fallback_env_var)
            if value:
                return value
        
        raise RuntimeError(f"Secret '{secret_name}' not configured")
```

**Integration Points**:
- `app/main.py`: Initialize SecretsManager at startup
- `app/configuracion/base_datos.py`: Retrieve DATABASE_PASSWORD
- `app/seguridad/token_manager.py`: Retrieve JWT_SECRET_KEY
- `app/utils/pdf_generator.py`: Retrieve PDF_PASSWORD

**Configuration**:

```env
# .env
AZURE_KEY_VAULT_URL=https://taller-vault.vault.azure.net/
# If not set, falls back to environment variables
```

**Azure Key Vault Setup**:
```bash
# Create Key Vault
az keyvault create --name taller-vault --resource-group taller-rg --location eastus

# Store secrets
az keyvault secret set --vault-name taller-vault --name "admin-password" --value "SecurePass123!"
az keyvault secret set --vault-name taller-vault --name "pdf-password" --value "PDFPass123!"
az keyvault secret set --vault-name taller-vault --name "jwt-secret-key" --value "$(openssl rand -base64 32)"
az keyvault secret set --vault-name taller-vault --name "database-password" --value "DBPass123!"

# Grant access to application identity
az keyvault set-policy --name taller-vault --object-id <app-identity-id> --secret-permissions get list
```

### 2. Docker Containerization

**Purpose**: Provide reproducible development and production environments.

**Files**:
- `Dockerfile`: Multi-stage build for production
- `Dockerfile.dev`: Development image with hot reload
- `docker-compose.yml`: Orchestration for all services
- `.dockerignore`: Exclude unnecessary files

**Dockerfile (Production)**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Create directories for uploads
RUN mkdir -p uploads/fotos uploads/compras

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/info')"

# Run with gunicorn
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+psycopg2://postgres:${DB_PASSWORD}@db:5432/taller_db?client_encoding=utf8
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - ENVIRONMENT=production
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./uploads:/app/uploads
    networks:
      - taller-network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: taller_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - taller-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - taller-network
    restart: unless-stopped

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+psycopg2://postgres:${DB_PASSWORD}@db:5432/taller_db?client_encoding=utf8
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
    networks:
      - taller-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  taller-network:
    driver: bridge
```

**.dockerignore**:
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.git/
.gitignore
.hypothesis/
.coverage
.env
.env.test
uploads/
frontend/node_modules/
frontend/dist/
*.md
!README.md
```

### 3. Alembic Database Migrations

**Purpose**: Version-controlled database schema changes with rollback capability.

**File Structure**:
```
migrations/
├── versions/
│   └── 001_initial_schema.py
├── env.py
├── script.py.mako
└── README
alembic.ini
```

**alembic.ini**:

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**migrations/env.py**:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.configuracion.base_datos import Base
from app.modelos import *  # Import all models

config = context.config

# Override sqlalchemy.url from environment
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Migration Workflow**:
```bash
# Initialize Alembic (one-time setup)
alembic init migrations

# Generate initial migration from current models
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Create new migration after model changes
alembic revision --autogenerate -m "Add new column to tickets"
```

### 4. Input Validation and Sanitization

**Purpose**: Prevent XSS attacks and validate file uploads.

**File**: `app/utils/input_validator.py`


```python
from typing import List
import bleach
import magic
from fastapi import UploadFile, HTTPException

# Configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf"
]

class InputSanitizer:
    """Sanitizes HTML input to prevent XSS attacks."""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove all HTML tags from text input.
        
        Args:
            text: Input text that may contain HTML
        
        Returns:
            Plain text with all HTML tags removed
        
        Example:
            >>> sanitize_html("<script>alert('xss')</script>Hello")
            "Hello"
        """
        if not text:
            return text
        
        # Remove all HTML tags
        return bleach.clean(text, tags=[], strip=True)
    
    @staticmethod
    def sanitize_dict(data: dict, fields: List[str]) -> dict:
        """
        Sanitize specific fields in a dictionary.
        
        Args:
            data: Dictionary containing fields to sanitize
            fields: List of field names to sanitize
        
        Returns:
            Dictionary with sanitized fields
        """
        sanitized = data.copy()
        for field in fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = InputSanitizer.sanitize_html(sanitized[field])
        return sanitized

class FileValidator:
    """Validates file uploads for size and type."""
    
    @staticmethod
    async def validate_file(file: UploadFile) -> UploadFile:
        """
        Validate file size and MIME type.
        
        Args:
            file: Uploaded file from FastAPI
        
        Returns:
            The same file if validation passes
        
        Raises:
            HTTPException: 413 if file too large, 415 if invalid type
        """
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024:.1f} MB"
            )
        
        # Detect MIME type from content (not from filename)
        mime = magic.from_buffer(content, mime=True)
        
        if mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type '{mime}' not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )
        
        return file
```

**Integration in Services**:
```python
# app/servicios/ticket_service.py
from app.utils.input_validator import InputSanitizer

class TicketService:
    def create_ticket(self, data: TicketCreate):
        # Sanitize text fields
        sanitized_data = InputSanitizer.sanitize_dict(
            data.dict(),
            fields=["motivo_visita", "observaciones"]
        )
        # Continue with ticket creation...
```

**Integration in Routes**:
```python
# app/rutas/upload_ruta.py
from app.utils.input_validator import FileValidator

@router.post("/upload/foto")
async def upload_foto(file: UploadFile = File(...)):
    # Validate file
    validated_file = await FileValidator.validate_file(file)
    # Continue with file processing...
```

### 5. HTTP Compression Middleware

**Purpose**: Reduce response size and improve load times.

**Integration in app/main.py**:

```python
from fastapi.middleware.gzip import GZipMiddleware

# Add after CORS middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=6     # Balance between speed and compression ratio (1-9)
)
```

**Configuration**:
- `minimum_size=1000`: Skip compression for small responses (overhead not worth it)
- `compresslevel=6`: Default level, good balance (1=fastest, 9=best compression)

**Expected Results**:
- JSON responses: 60-70% size reduction
- HTML responses: 70-80% size reduction
- Already compressed files (images, PDFs): No additional compression

### 6. Async PDF Generation with Celery

**Purpose**: Offload PDF generation to background workers to avoid blocking API requests.

**File**: `app/tasks/celery_app.py`

```python
from celery import Celery
import os

# Initialize Celery
celery_app = Celery(
    "taller_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Bogota",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    result_expires=86400,  # Results expire after 24 hours
)
```

**File**: `app/tasks/pdf_tasks.py`

```python
from app.tasks.celery_app import celery_app
from app.utils.pdf_generator import generar_pdf_ticket
from app.configuracion.base_datos import SessionLocal
import os
from datetime import datetime

@celery_app.task(bind=True, name="generate_ticket_pdf")
def generate_ticket_pdf_task(self, ticket_id: int) -> dict:
    """
    Generate PDF for a ticket asynchronously.
    
    Args:
        ticket_id: ID of the ticket to generate PDF for
    
    Returns:
        dict with status and file_path
    """
    db = SessionLocal()
    try:
        # Generate PDF
        pdf_path = generar_pdf_ticket(ticket_id, db)
        
        return {
            "status": "completed",
            "file_path": pdf_path,
            "ticket_id": ticket_id,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "ticket_id": ticket_id
        }
    finally:
        db.close()
```

**File**: `app/rutas/pdf_ruta.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.configuracion.base_datos import obtener_db
from app.tasks.pdf_tasks import generate_ticket_pdf_task
from celery.result import AsyncResult

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])

@router.post("/tickets/{ticket_id}/generate")
async def generate_ticket_pdf(
    ticket_id: int,
    db: Session = Depends(obtener_db)
):
    """
    Start async PDF generation for a ticket.
    
    Returns task_id to check status.
    """
    # Verify ticket exists
    from app.repositorios.ticket_repository import TicketRepository
    ticket_repo = TicketRepository(db)
    ticket = ticket_repo.get_by_id(ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Start async task
    task = generate_ticket_pdf_task.delay(ticket_id)
    
    return {
        "task_id": task.id,
        "status": "processing",
        "ticket_id": ticket_id
    }

@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Check status of PDF generation task."""
    task_result = AsyncResult(task_id)
    
    if task_result.ready():
        result = task_result.get()
        return {
            "task_id": task_id,
            "status": result.get("status"),
            "result": result
        }
    else:
        return {
            "task_id": task_id,
            "status": "processing"
        }

@router.get("/tasks/{task_id}/result")
async def download_pdf(task_id: str):
    """Download generated PDF."""
    from fastapi.responses import FileResponse
    
    task_result = AsyncResult(task_id)
    
    if not task_result.ready():
        raise HTTPException(status_code=202, detail="PDF still processing")
    
    result = task_result.get()
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    file_path = result.get("file_path")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path)
    )
```

**Celery Worker Startup**:
```bash
# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# With concurrency
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

### 7. Complete Type Hints

**Purpose**: Enable static type checking and improve IDE support.

**Example Transformations**:


```python
# Before (no type hints)
def get_by_username(self, username):
    return self.db.query(User).filter(User.username == username).first()

# After (with type hints)
from typing import Optional
from app.modelos.user import User

def get_by_username(self, username: str) -> Optional[User]:
    return self.db.query(User).filter(User.username == username).first()
```

```python
# Before
def authenticate(self, username, password, ip_address, user_agent):
    # ...

# After
from typing import Dict, Any

def authenticate(
    self,
    username: str,
    password: str,
    ip_address: str,
    user_agent: str
) -> Dict[str, Any]:
    # ...
```

**mypy Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "reportlab.*",
    "zeroconf.*",
    "slowapi.*",
]
ignore_missing_imports = true
```

**Running mypy**:
```bash
# Check all files
mypy app/

# Check specific module
mypy app/servicios/

# Generate HTML report
mypy app/ --html-report mypy-report/
```

### 8. Ruff Linter Configuration

**Purpose**: Enforce code quality standards and consistent formatting.

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = [
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "migrations",
    ".hypothesis",
]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__.py
"app/modelos/*.py" = ["ARG002"]  # Allow unused method arguments in models

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**Pre-commit Hook** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

**Setup Pre-commit**:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**Usage**:
```bash
# Check for issues
ruff check app/

# Auto-fix issues
ruff check app/ --fix

# Format code
ruff format app/

# Check and format
ruff check app/ --fix && ruff format app/
```

### 9. Enhanced API Documentation

**Purpose**: Provide comprehensive, interactive API documentation.

**Enhanced Endpoint Example**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.esquemas.ticket_schema import TicketCreate, TicketResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
    description="""
    Create a new service ticket for a vehicle.
    
    This endpoint creates a ticket with initial status 'ABIERTO' and associates it
    with a vehicle by plate number. If the vehicle doesn't exist, it will be created.
    
    **Required permissions**: MECANICO, RECEPCIONISTA, or ADMIN role
    
    **Rate limit**: 30 requests per minute
    """,
    responses={
        201: {
            "description": "Ticket created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "placa": "ABC123",
                        "motivo_visita": "Cambio de aceite",
                        "estado": "ABIERTO",
                        "fecha_ingreso": "2026-04-06T10:30:00",
                        "kilometraje": 15000
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Invalid plate format",
                        "details": {"field": "placa", "issue": "must be 6 characters"}
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "authentication_failed",
                        "message": "Token expired or invalid"
                    }
                }
            }
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": "insufficient_permissions",
                        "message": "User role SOLO_LECTURA cannot create tickets"
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests",
                        "retry_after": 60
                    }
                }
            }
        }
    }
)
async def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(obtener_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new service ticket."""
    # Implementation...
```

**Enhanced Schema with Examples**:

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TicketCreate(BaseModel):
    placa: str = Field(
        ...,
        description="Vehicle license plate (6 characters)",
        example="ABC123",
        min_length=6,
        max_length=6
    )
    motivo_visita: str = Field(
        ...,
        description="Reason for service visit",
        example="Cambio de aceite y revisión general"
    )
    kilometraje: Optional[int] = Field(
        None,
        description="Current vehicle mileage",
        example=15000,
        ge=0
    )
    observaciones: Optional[str] = Field(
        None,
        description="Additional observations or notes",
        example="Cliente reporta ruido en el motor"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "placa": "ABC123",
                "motivo_visita": "Cambio de aceite",
                "kilometraje": 15000,
                "observaciones": "Cliente solicita revisión completa"
            }
        }
```

**OpenAPI Customization** (`app/main.py`):
```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Taller Mecánico API",
        version="1.1.0",
        description="""
        # API de Gestión de Taller Mecánico
        
        Sistema completo para gestión de talleres de motos con:
        - Gestión de tickets de servicio
        - Control de vehículos y clientes
        - Administración de procesos y repuestos
        - Sistema de pagos y economía
        - Autenticación JWT con roles
        - Auditoría completa de eventos
        
        ## Autenticación
        
        La API usa JWT (JSON Web Tokens) para autenticación:
        
        1. Obtener token: `POST /auth/login`
        2. Usar token en header: `Authorization: Bearer <token>`
        3. Refrescar token: `POST /auth/refresh`
        
        ## Rate Limiting
        
        - Login: 5 req/min
        - Creación: 30 req/min
        - Lectura: 100 req/min
        
        ## Roles
        
        - **ADMIN**: Acceso completo
        - **MECANICO**: Gestión de tickets y procesos
        - **RECEPCIONISTA**: Creación de tickets y consultas
        - **SOLO_LECTURA**: Solo consultas
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token obtained from /auth/login"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**Export OpenAPI Schema**:
```bash
# Generate openapi.json
python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
```

## Data Models

No new database models are required for this spec. All improvements work with existing models:

- `User`: For authentication and authorization
- `Ticket`: For PDF generation
- `AuditLog`: For security event logging
- Existing models remain unchanged

**Configuration Model** (new file: `app/modelos/app_config.py`):
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
    """Application configuration loaded from environment and secrets."""
    
    # Database
    database_url: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # Secrets Manager
    azure_key_vault_url: Optional[str] = None
    use_key_vault: bool = False
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_mime_types: list = None
    
    # Environment
    environment: str = "development"
    
    def __post_init__(self):
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                "image/jpeg",
                "image/png",
                "image/webp",
                "application/pdf"
            ]
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following testable properties and examples. Many criteria relate to configuration, documentation, and tooling setup which are not suitable for property-based testing. The testable behaviors focus on:

1. **Input sanitization**: HTML removal should work for all inputs
2. **File validation**: Size and type checks should work for all files
3. **HTTP compression**: Compression should work for all eligible responses
4. **Database migrations**: Upgrade/downgrade should be reversible
5. **Error handling**: Specific error conditions should produce correct responses

**Redundancy Analysis**:
- Criteria 4.1 and 4.2 are identical (HTML sanitization) - combined into Property 1
- File validation criteria 4.4 and 4.5 are separate concerns (size vs type) - kept separate
- Compression criteria 5.2 and 5.3 are related but test different aspects - kept separate

### Property 1: HTML Sanitization Removes All Tags

*For any* string containing HTML tags, the sanitizer should remove all HTML tags and return only plain text content.

**Validates: Requirements 4.1, 4.2**

### Property 2: File Size Validation Rejects Oversized Files

*For any* file with size greater than MAX_FILE_SIZE (10 MB), the file validator should reject the file with HTTP 413 error.

**Validates: Requirements 4.4, 4.6**

### Property 3: MIME Type Validation Rejects Invalid Types

*For any* file with MIME type not in ALLOWED_MIME_TYPES list, the file validator should reject the file with HTTP 415 error.

**Validates: Requirements 4.5, 4.7**

### Property 4: GZip Compression Activates for Large Responses

*For any* HTTP response larger than 1000 bytes, when the client sends Accept-Encoding: gzip header, the response should be compressed and include Content-Encoding: gzip header.

**Validates: Requirements 5.2, 5.3**

### Property 5: Database Migration Round Trip Preserves State

*For any* database state, applying a migration with `alembic upgrade +1` followed by `alembic downgrade -1` should restore the original database state.

**Validates: Requirements 3.4**

## Error Handling

### Secrets Manager Errors

**Scenario**: Azure Key Vault unavailable or secret not found

**Handling**:
```python
class SecretsManager:
    def get_secret(self, secret_name: str, fallback_env_var: Optional[str] = None) -> str:
        if self.use_key_vault:
            try:
                secret = self.client.get_secret(secret_name)
                return secret.value
            except ResourceNotFoundError:
                if fallback_env_var:
                    value = os.getenv(fallback_env_var)
                    if value:
                        return value
                raise RuntimeError(f"Secret '{secret_name}' not found in Key Vault")
        
        # Fallback to environment variable
        if fallback_env_var:
            value = os.getenv(fallback_env_var)
            if value:
                return value
        
        raise RuntimeError(f"Secret '{secret_name}' not configured")
```

**Error Response**: Application fails to start with clear error message indicating which secret is missing.

### File Upload Errors

**Scenario 1**: File too large (> 10 MB)

**Response**:
```json
{
  "status_code": 413,
  "error": "payload_too_large",
  "message": "File size exceeds maximum allowed size of 10.0 MB"
}
```

**Scenario 2**: Invalid MIME type

**Response**:
```json
{
  "status_code": 415,
  "error": "unsupported_media_type",
  "message": "File type 'application/exe' not allowed. Allowed types: image/jpeg, image/png, image/webp, application/pdf"
}
```

### Celery Task Errors

**Scenario**: PDF generation fails

**Handling**:
```python
@celery_app.task(bind=True, name="generate_ticket_pdf")
def generate_ticket_pdf_task(self, ticket_id: int) -> dict:
    db = SessionLocal()
    try:
        pdf_path = generar_pdf_ticket(ticket_id, db)
        return {
            "status": "completed",
            "file_path": pdf_path,
            "ticket_id": ticket_id,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        # Log error with full context
        logger.error(f"PDF generation failed for ticket {ticket_id}: {str(e)}", exc_info=True)
        
        return {
            "status": "failed",
            "error": str(e),
            "ticket_id": ticket_id,
            "failed_at": datetime.now().isoformat()
        }
    finally:
        db.close()
```

**Task Status Response**:
```json
{
  "task_id": "abc-123-def",
  "status": "failed",
  "result": {
    "status": "failed",
    "error": "Ticket not found",
    "ticket_id": 999,
    "failed_at": "2026-04-06T15:30:00"
  }
}
```

### Database Migration Errors

**Scenario**: Migration fails mid-execution

**Handling**: Alembic uses database transactions. If a migration fails, the transaction is rolled back automatically, leaving the database in its previous state.

**Error Output**:
```
ERROR [alembic.runtime.migration] Error running migration: ...
ROLLBACK
```

**Recovery**: Fix the migration script and re-run `alembic upgrade head`.

### Type Checking Errors

**Scenario**: mypy detects type errors

**Example Output**:
```
app/servicios/auth_service.py:45: error: Argument 1 to "authenticate" has incompatible type "int"; expected "str"
app/repositorios/user_repository.py:23: error: Incompatible return value type (got "None", expected "User")
Found 2 errors in 2 files (checked 45 source files)
```

**Handling**: Fix type errors before committing code. CI/CD pipeline should run mypy and fail on errors.

### Linting Errors

**Scenario**: Ruff detects code quality issues

**Example Output**:
```
app/servicios/ticket_service.py:12:1: F401 [*] `app.modelos.user.User` imported but unused
app/rutas/ticket_ruta.py:45:80: E501 Line too long (105 > 100 characters)
Found 2 errors.
[*] 1 fixable with the `--fix` option.
```

**Handling**: Run `ruff check --fix` to auto-fix issues. Pre-commit hook prevents commits with unfixed issues.


## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, configuration, and integration points
- **Property tests**: Verify universal properties across all inputs (sanitization, validation, compression)

Both testing approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Property-Based Testing

**Library**: `hypothesis` (already in use in the project)

**Configuration**: Each property test should run minimum 100 iterations to ensure comprehensive input coverage.

**Test Structure**:
```python
from hypothesis import given, strategies as st
import pytest

# Feature: mejoras-calidad-sistema, Property 1: HTML Sanitization Removes All Tags
@given(html_input=st.text())
def test_sanitizer_removes_all_html_tags(html_input):
    """
    Property: For any string containing HTML tags, sanitizer removes all tags.
    
    Feature: mejoras-calidad-sistema, Property 1: HTML Sanitization Removes All Tags
    """
    from app.utils.input_validator import InputSanitizer
    
    # Add some HTML tags to the input
    html_with_tags = f"<script>alert('xss')</script>{html_input}<b>bold</b>"
    
    result = InputSanitizer.sanitize_html(html_with_tags)
    
    # Property: Result should not contain any HTML tags
    assert "<" not in result
    assert ">" not in result
    assert "script" not in result.lower() or "script" in html_input.lower()
```

### Unit Testing

**Test Files**:
- `tests/unit/test_secrets_manager.py`: Secrets retrieval and fallback
- `tests/unit/test_input_validator.py`: Sanitization and file validation
- `tests/unit/test_celery_tasks.py`: Async PDF generation
- `tests/integration/test_docker_setup.py`: Docker compose services
- `tests/integration/test_alembic_migrations.py`: Migration workflow

**Example Unit Tests**:

```python
# tests/unit/test_secrets_manager.py
import pytest
from unittest.mock import Mock, patch
from app.configuracion.secrets_manager import SecretsManager

def test_secrets_manager_retrieves_from_key_vault():
    """Test that secrets are retrieved from Azure Key Vault when configured."""
    with patch('app.configuracion.secrets_manager.SecretClient') as mock_client:
        mock_secret = Mock()
        mock_secret.value = "secret_value_123"
        mock_client.return_value.get_secret.return_value = mock_secret
        
        with patch.dict('os.environ', {'AZURE_KEY_VAULT_URL': 'https://test.vault.azure.net/'}):
            manager = SecretsManager()
            result = manager.get_secret("test-secret")
            
            assert result == "secret_value_123"
            mock_client.return_value.get_secret.assert_called_once_with("test-secret")

def test_secrets_manager_falls_back_to_env_var():
    """Test that secrets fall back to environment variables when Key Vault not configured."""
    with patch.dict('os.environ', {'TEST_SECRET': 'env_value_456'}, clear=True):
        manager = SecretsManager()
        result = manager.get_secret("test-secret", fallback_env_var="TEST_SECRET")
        
        assert result == "env_value_456"

def test_secrets_manager_raises_error_when_secret_not_found():
    """Test that missing secrets raise RuntimeError."""
    manager = SecretsManager()
    
    with pytest.raises(RuntimeError, match="Secret 'missing-secret' not configured"):
        manager.get_secret("missing-secret")
```

```python
# tests/unit/test_input_validator.py
import pytest
from fastapi import UploadFile, HTTPException
from io import BytesIO
from app.utils.input_validator import InputSanitizer, FileValidator

def test_sanitizer_removes_script_tags():
    """Test that script tags are removed from input."""
    input_text = "<script>alert('xss')</script>Hello World"
    result = InputSanitizer.sanitize_html(input_text)
    assert result == "Hello World"
    assert "<script>" not in result

def test_sanitizer_removes_all_html_tags():
    """Test that all HTML tags are removed."""
    input_text = "<div><p>Text</p><b>Bold</b></div>"
    result = InputSanitizer.sanitize_html(input_text)
    assert result == "TextBold"
    assert "<" not in result
    assert ">" not in result

@pytest.mark.asyncio
async def test_file_validator_rejects_oversized_file():
    """Test that files larger than 10MB are rejected with HTTP 413."""
    # Create a file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)
    file = UploadFile(filename="large.jpg", file=BytesIO(large_content))
    
    with pytest.raises(HTTPException) as exc_info:
        await FileValidator.validate_file(file)
    
    assert exc_info.value.status_code == 413
    assert "exceeds maximum" in exc_info.value.detail

@pytest.mark.asyncio
async def test_file_validator_rejects_invalid_mime_type():
    """Test that files with invalid MIME types are rejected with HTTP 415."""
    # Create a file with invalid MIME type (e.g., executable)
    exe_content = b"MZ\x90\x00"  # PE executable header
    file = UploadFile(filename="malware.exe", file=BytesIO(exe_content))
    
    with pytest.raises(HTTPException) as exc_info:
        await FileValidator.validate_file(file)
    
    assert exc_info.value.status_code == 415
    assert "not allowed" in exc_info.value.detail
```

```python
# tests/integration/test_alembic_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

def test_migration_upgrade_and_downgrade():
    """Test that migrations can be applied and reverted."""
    # Setup test database
    test_db_url = "postgresql://test:test@localhost:5432/test_db"
    engine = create_engine(test_db_url)
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    
    # Get initial state
    inspector = inspect(engine)
    initial_tables = set(inspector.get_table_names())
    
    # Apply one migration
    command.upgrade(alembic_cfg, "+1")
    
    # Verify migration was applied
    inspector = inspect(engine)
    after_upgrade_tables = set(inspector.get_table_names())
    assert after_upgrade_tables != initial_tables
    
    # Revert migration
    command.downgrade(alembic_cfg, "-1")
    
    # Verify state was restored
    inspector = inspect(engine)
    after_downgrade_tables = set(inspector.get_table_names())
    assert after_downgrade_tables == initial_tables
```

### Integration Testing

**Docker Compose Testing**:
```bash
# Test that all services start correctly
docker-compose up -d
docker-compose ps | grep "Up" | wc -l  # Should be 4 (api, db, redis, celery_worker)

# Test API is accessible
curl http://localhost:8000/info

# Test database is accessible
docker-compose exec db psql -U postgres -d taller_db -c "SELECT 1"

# Test Redis is accessible
docker-compose exec redis redis-cli ping

# Cleanup
docker-compose down -v
```

**Celery Task Testing**:
```python
# tests/integration/test_celery_tasks.py
import pytest
from app.tasks.pdf_tasks import generate_ticket_pdf_task
from app.tasks.celery_app import celery_app

@pytest.mark.celery
def test_pdf_generation_task_completes_successfully():
    """Test that PDF generation task completes for valid ticket."""
    # Create test ticket
    ticket_id = 1
    
    # Execute task synchronously for testing
    result = generate_ticket_pdf_task.apply(args=[ticket_id]).get()
    
    assert result["status"] == "completed"
    assert "file_path" in result
    assert result["ticket_id"] == ticket_id

@pytest.mark.celery
def test_pdf_generation_task_fails_for_invalid_ticket():
    """Test that PDF generation task fails gracefully for invalid ticket."""
    ticket_id = 99999  # Non-existent ticket
    
    result = generate_ticket_pdf_task.apply(args=[ticket_id]).get()
    
    assert result["status"] == "failed"
    assert "error" in result
```

### Test Coverage Goals

- **Input Validation**: 100% coverage (critical security component)
- **Secrets Manager**: 90% coverage (exclude Azure SDK internals)
- **Celery Tasks**: 85% coverage (exclude Celery framework code)
- **Overall**: Maintain existing 52% backend coverage, focus on new components

### Continuous Integration

**CI Pipeline Steps**:
1. Run mypy type checking (must pass with 0 errors)
2. Run ruff linting (must pass with 0 errors)
3. Run unit tests with pytest
4. Run property-based tests with hypothesis (100 iterations minimum)
5. Run integration tests (Docker, Alembic, Celery)
6. Generate coverage report
7. Build Docker images
8. Run security scan (bandit, safety)

**Pre-commit Hooks**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict]
```

