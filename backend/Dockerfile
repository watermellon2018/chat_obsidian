# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies in an isolated layer (cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy all backend source code
COPY . .

# The vault is mounted at runtime via Docker volume — do not bake it in.
# Default path: /vault (override with VAULT_PATH env var)
ENV VAULT_PATH=/vault \
    PORT=8005 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8005

# uvicorn imports main:app which calls _build_app() using MODEL_BACKEND env var.
# Pass MODEL_BACKEND=gemini (default) or MODEL_BACKEND=ollama at runtime.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
