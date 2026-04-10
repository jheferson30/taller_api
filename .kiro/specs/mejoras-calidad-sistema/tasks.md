# Implementation Plan: System Quality Improvements

## Overview

This plan implements 9 non-critical quality improvements to enhance security posture, developer experience, code quality, and operational readiness. The improvements are organized into logical groups with dependencies managed through task ordering.

These improvements should be implemented AFTER the critical security fixes in the "correcciones-auditoria-sistema" spec.

## Tasks

- [x] 1. Setup infrastructure dependencies and configuration
  - [x] 1.1 Install and configure new Python dependencies
    - Add to requirements.txt: azure-identity, azure-keyvault-secrets, celery[redis], redis, alembic, bleach, python-magic, mypy, ruff, pre-commit
    - Install dependencies with pip
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 6.1, 7.4, 8.1_
  
  - [x] 1.2 Create application configuration model
    - Create `app/modelos/app_config.py` with AppConfig dataclass
    - Define configuration fields for all new components
    - _Requirements: 1.1, 6.1_
  
  - [x] 1.3 Configure mypy for type checking
    - Create `pyproject.toml` with mypy configuration in strict mode
    - Configure module overrides for third-party libraries without type stubs
    - _Requirements: 7.8_
  
  - [x] 1.4 Configure Ruff linter and formatter
    - Add Ruff configuration to `pyproject.toml`
    - Enable rules: pycodestyle (E/W), pyflakes (F), isort (I), flake8-bugbear (B)
    - Set line length to 100 characters
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [x] 1.5 Setup pre-commit hooks
    - Create `.pre-commit-config.yaml` with Ruff and mypy hooks
    - Install pre-commit hooks with `pre-commit install`
    - _Requirements: 8.8_

- [x] 2. Implement Secrets Manager integration
  - [x] 2.1 Create SecretsManager class
    - Create `app/configuracion/secrets_manager.py`
    - Implement Azure Key Vault integration with DefaultAzureCredential
    - Implement fallback to environment variables for development
    - Add get_secret method with error handling
    - _Requirements: 1.1, 1.2, 1.4, 1.7_
  
  - [x] 2.2 Write unit tests for SecretsManager
    - Test Key Vault retrieval with mocked Azure SDK
    - Test fallback to environment variables
    - Test error handling for missing secrets
    - _Requirements: 1.6_
  
  - [x] 2.3 Integrate SecretsManager in application startup
    - Modify `app/main.py` to initialize SecretsManager at startup
    - Update `app/configuracion/base_datos.py` to retrieve DATABASE_PASSWORD from secrets
    - Update `app/seguridad/token_manager.py` to retrieve JWT_SECRET_KEY from secrets
    - _Requirements: 1.2, 1.3_
  
  - [x] 2.4 Update environment configuration
    - Add AZURE_KEY_VAULT_URL to `.env.example`
    - Document Key Vault setup process in README.md
    - _Requirements: 1.8_

- [x] 3. Implement Docker containerization
  - [x] 3.1 Create production Dockerfile
    - Create multi-stage Dockerfile with Python 3.11-slim base
    - Configure builder stage with dependencies
    - Configure runtime stage with application code
    - Add health check endpoint
    - Configure gunicorn with uvicorn workers
    - _Requirements: 2.1, 2.7_
  
  - [x] 3.2 Create docker-compose.yml
    - Define services: api, db (PostgreSQL 15), redis, celery_worker
    - Configure environment variables and volumes
    - Setup service dependencies and health checks
    - Configure networking between services
    - _Requirements: 2.2, 2.3, 2.5, 2.6_
  
  - [x] 3.3 Create .dockerignore file
    - Exclude __pycache__, .git, .env, uploads, node_modules
    - _Requirements: 2.1_
  
  - [x] 3.4 Document Docker usage
    - Add Docker commands to README.md with examples
    - Document environment variable configuration
    - _Requirements: 2.8_

- [x] 4. Setup Alembic database migrations
  - [x] 4.1 Initialize Alembic configuration
    - Run `alembic init migrations` to create directory structure
    - Configure `alembic.ini` with database connection settings
    - _Requirements: 3.1_
  
  - [x] 4.2 Configure Alembic environment
    - Modify `migrations/env.py` to import all models
    - Configure target_metadata from Base.metadata
    - Add support for DATABASE_URL environment variable override
    - _Requirements: 3.1, 3.6_
  
  - [x] 4.3 Generate initial migration
    - Run `alembic revision --autogenerate -m "Initial schema"`
    - Review and adjust generated migration script
    - Store migration in `migrations/versions/`
    - _Requirements: 3.2, 3.5_
  
  - [x]* 4.4 Write integration tests for migrations
    - Test upgrade applies migration successfully
    - Test downgrade reverts migration (Property 5: Database Migration Round Trip)
    - Test migration history tracking
    - _Requirements: 3.3, 3.4_
  
  - [x] 4.5 Document migration workflow
    - Add migration commands to README.md
    - Document workflow for creating and applying migrations
    - _Requirements: 3.8_

- [x] 5. Checkpoint - Verify infrastructure setup
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement input validation and sanitization
  - [x] 6.1 Create InputSanitizer class
    - Create `app/utils/input_validator.py`
    - Implement sanitize_html method using bleach to remove all HTML tags
    - Implement sanitize_dict method for batch field sanitization
    - Define MAX_FILE_SIZE and ALLOWED_MIME_TYPES constants
    - _Requirements: 4.1, 4.2, 4.8_
  
  - [x]* 6.2 Write property test for HTML sanitization
    - **Property 1: HTML Sanitization Removes All Tags**
    - **Validates: Requirements 4.1, 4.2**
    - Use hypothesis to generate random HTML inputs
    - Verify all HTML tags are removed from output
  
  - [x] 6.3 Create FileValidator class
    - Implement validate_file method for UploadFile validation
    - Check file size against MAX_FILE_SIZE (10 MB)
    - Detect MIME type using python-magic from file content
    - Validate MIME type against ALLOWED_MIME_TYPES
    - Raise HTTPException 413 for oversized files
    - Raise HTTPException 415 for invalid MIME types
    - _Requirements: 4.4, 4.5, 4.6, 4.7_
  
  - [x]* 6.4 Write property tests for file validation
    - **Property 2: File Size Validation Rejects Oversized Files**
    - **Validates: Requirements 4.4, 4.6**
    - **Property 3: MIME Type Validation Rejects Invalid Types**
    - **Validates: Requirements 4.5, 4.7**
  
  - [x]* 6.5 Write unit tests for input validation
    - Test sanitizer removes script tags and all HTML
    - Test file validator rejects oversized files with HTTP 413
    - Test file validator rejects invalid MIME types with HTTP 415
    - Test file validator accepts valid files
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
  
  - [x] 6.6 Integrate sanitization in services
    - Update `app/servicios/ticket_service.py` to sanitize motivo_visita and observaciones
    - Update `app/servicios/proceso_service.py` to sanitize descripcion_proceso
    - Update other services with text input fields
    - _Requirements: 4.3_
  
  - [x] 6.7 Integrate file validation in upload routes
    - Update `app/rutas/upload_ruta.py` to validate uploaded files
    - Apply FileValidator.validate_file to all file upload endpoints
    - _Requirements: 4.4, 4.5_

- [x] 7. Implement HTTP compression
  - [x] 7.1 Add GZip middleware to FastAPI application
    - Modify `app/main.py` to add GZipMiddleware after CORS
    - Configure minimum_size=1000 bytes
    - Configure compresslevel=6 for balanced compression
    - _Requirements: 5.1, 5.2, 5.5_
  
  - [x]* 7.2 Write property test for compression
    - **Property 4: GZip Compression Activates for Large Responses**
    - **Validates: Requirements 5.2, 5.3**
    - Generate responses of varying sizes
    - Verify compression activates for responses > 1000 bytes
    - Verify Content-Encoding header is set correctly
  
  - [x]* 7.3 Write integration tests for compression
    - Test compression activates with Accept-Encoding: gzip header
    - Test compression reduces JSON response size by at least 60%
    - Test small responses are not compressed
    - _Requirements: 5.3, 5.4, 5.6_

- [x] 8. Implement async PDF generation with Celery
  - [x] 8.1 Create Celery application configuration
    - Create `app/tasks/celery_app.py`
    - Initialize Celery with Redis broker and backend
    - Configure task serialization, timezone, and timeouts
    - _Requirements: 6.1, 6.8_
  
  - [x] 8.2 Create PDF generation task
    - Create `app/tasks/pdf_tasks.py`
    - Implement generate_ticket_pdf_task as Celery task
    - Handle database session management in task
    - Return task result with status, file_path, and error handling
    - _Requirements: 6.2, 6.5, 6.7_
  
  - [x] 8.3 Create PDF API routes
    - Create `app/rutas/pdf_ruta.py` with router
    - Implement POST `/pdf/tickets/{ticket_id}/generate` to start async task
    - Implement GET `/pdf/tasks/{task_id}/status` to check task status
    - Implement GET `/pdf/tasks/{task_id}/result` to download generated PDF
    - _Requirements: 6.3, 6.4, 6.6_
  
  - [x]* 8.4 Write unit tests for Celery tasks
    - Test PDF generation task completes successfully for valid ticket
    - Test PDF generation task fails gracefully for invalid ticket
    - Test task returns correct status and file_path
    - _Requirements: 6.2, 6.5, 6.7_
  
  - [x]* 8.5 Write integration tests for PDF API
    - Test async task creation returns task_id
    - Test task status endpoint returns correct status
    - Test PDF download endpoint returns file
    - _Requirements: 6.3, 6.4, 6.6_
  
  - [x] 8.6 Update docker-compose for Celery worker
    - Verify celery_worker service is configured in docker-compose.yml
    - Ensure worker has access to database and Redis
    - _Requirements: 6.1_
  
  - [x] 8.7 Implement PDF cleanup task
    - Create scheduled Celery task to delete PDFs older than 24 hours
    - Configure Celery beat for periodic execution
    - _Requirements: 6.9_

- [x] 9. Checkpoint - Verify core functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Add complete type hints to codebase
  - [x] 10.1 Add type hints to repository layer
    - Add type hints to all methods in `app/repositorios/`
    - Use Optional, List, Dict from typing module
    - Use specific model types for return values
    - _Requirements: 7.1, 7.2, 7.7_
  
  - [x] 10.2 Add type hints to service layer
    - Add type hints to all methods in `app/servicios/`
    - Document parameter types and return types
    - _Requirements: 7.1, 7.2, 7.6_
  
  - [x] 10.3 Add type hints to routes layer
    - Add type hints to all route handlers in `app/rutas/`
    - Use FastAPI dependency types correctly
    - _Requirements: 7.1, 7.2_
  
  - [x] 10.4 Run mypy validation
    - Execute `mypy app/` to check for type errors
    - Fix all type errors reported by mypy
    - Verify 0 errors in mypy output
    - _Requirements: 7.4, 7.5_
  
  - [ ]* 10.5 Verify type hint coverage
    - Run coverage analysis for type hints
    - Ensure at least 90% coverage of functions have type hints
    - _Requirements: 7.3_

- [x] 11. Apply Ruff linting and formatting
  - [x] 11.1 Run Ruff linter on codebase
    - Execute `ruff check app/` to identify code quality issues
    - Review reported violations
    - _Requirements: 8.5_
  
  - [x] 11.2 Auto-fix Ruff issues
    - Execute `ruff check app/ --fix` to automatically fix issues
    - Review changes made by auto-fix
    - _Requirements: 8.5_
  
  - [x] 11.3 Format code with Ruff
    - Execute `ruff format app/` to format all Python files
    - Verify consistent code formatting
    - _Requirements: 8.6_
  
  - [x] 11.4 Verify Ruff compliance
    - Run `ruff check app/` again to ensure 0 violations
    - Commit formatted code
    - _Requirements: 8.5_
  
  - [x] 11.5 Test pre-commit hooks
    - Make a test commit to verify pre-commit hooks run
    - Verify Ruff and mypy execute automatically
    - _Requirements: 8.8_
  
  - [x] 11.6 Update documentation for linting
    - Add Ruff commands to README.md
    - Document pre-commit hook usage
    - _Requirements: 8.9_

- [x] 12. Enhance API documentation
  - [x] 12.1 Add detailed descriptions to main endpoints
    - Update ticket endpoints with comprehensive descriptions
    - Update authentication endpoints with usage examples
    - Update vehicle, payment, and user endpoints
    - _Requirements: 9.1, 9.4_
  
  - [x] 12.2 Add request/response examples to endpoints
    - Add example request bodies to POST/PUT endpoints
    - Add example response bodies for success cases
    - Add example error responses for 400, 401, 403, 404, 422, 500
    - _Requirements: 9.2, 9.3_
  
  - [x] 12.3 Enhance Pydantic schemas with examples
    - Add Field descriptions to all schema fields
    - Add schema_extra with complete examples
    - Document validation constraints
    - _Requirements: 9.5_
  
  - [x] 12.4 Customize OpenAPI schema
    - Create custom_openapi function in `app/main.py`
    - Add comprehensive API description with authentication guide
    - Add security scheme for JWT Bearer authentication
    - Document rate limits for each endpoint category
    - _Requirements: 9.6, 9.9_
  
  - [x] 12.5 Export OpenAPI schema
    - Generate `openapi.json` file for client generation
    - Verify schema is valid and complete
    - _Requirements: 9.8_
  
  - [x] 12.6 Verify documentation completeness
    - Access `/docs` endpoint and review interactive documentation
    - Test example requests in Swagger UI
    - Verify all endpoints are documented with examples
    - _Requirements: 9.7_

- [x] 13. Final integration and verification
  - [x] 13.1 Build and test Docker containers
    - Build production Docker image
    - Start all services with docker-compose up
    - Verify all services are healthy
    - Test API endpoints through Docker
    - _Requirements: 2.3_
  
  - [x] 13.2 Test complete workflow end-to-end
    - Test secrets retrieval from Key Vault (or fallback)
    - Test database migrations apply successfully
    - Test input sanitization on ticket creation
    - Test file upload validation
    - Test async PDF generation workflow
    - Test HTTP compression on large responses
    - _Requirements: 1.2, 3.3, 4.2, 4.4, 5.2, 6.2_
  
  - [x] 13.3 Run full test suite
    - Execute all unit tests with pytest
    - Execute all property-based tests with hypothesis
    - Execute all integration tests
    - Verify test coverage meets goals
    - _Requirements: 7.5, 8.5_
  
  - [x] 13.4 Verify code quality standards
    - Run mypy and verify 0 type errors
    - Run ruff and verify 0 violations
    - Verify pre-commit hooks are working
    - _Requirements: 7.5, 8.5_
  
  - [x] 13.5 Update project documentation
    - Update README.md with all new features
    - Document setup instructions for Azure Key Vault
    - Document Docker usage and commands
    - Document Alembic migration workflow
    - Document Celery worker setup
    - Document code quality tools (mypy, ruff)
    - _Requirements: 1.8, 2.8, 3.8, 8.9_

- [x] 14. Final checkpoint - Complete verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at logical breaks
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and integration points
- These improvements are non-critical and should be implemented AFTER critical security fixes
- Docker setup enables consistent development and production environments
- Type hints and linting improve code quality and maintainability
- Async PDF generation prevents blocking API requests during report generation
