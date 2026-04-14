# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies in an isolated layer (cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# The vault is mounted at runtime via Docker volume — do not bake it in.
# Default path: /vault (override with VAULT_PATH env var)
ENV PORT=8000 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

WORKDIR /app/backend
# uvicorn imports main:app which calls _build_app() using MODEL_BACKEND env var.
# Pass MODEL_BACKEND=openrouter (default) or MODEL_BACKEND=ollama at runtime.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
