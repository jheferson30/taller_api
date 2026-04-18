# ── Stage 1: Build Frontend ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./

# Set VITE_API_URL to empty for production (uses relative URLs)
# CRITICAL: Vite needs this at build time, not runtime
ENV VITE_API_URL=""

# Build with production mode explicitly
RUN npm run build -- --mode production

# ── Stage 2: Build Python deps ────────────────────────────────────────────────
FROM python:3.11-slim AS python-builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 3: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# App code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY alembic.ini .

# Frontend build
COPY --from=frontend-builder /frontend/dist ./frontend/dist
COPY --from=frontend-builder /frontend/public ./frontend/public

# Uploads dirs
RUN mkdir -p uploads/fotos uploads/compras uploads/firmas uploads/logo

# Entrypoint
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/info || exit 1

ENTRYPOINT ["scripts/entrypoint.sh"]
