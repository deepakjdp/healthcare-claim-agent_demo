# ──────────────────────────────────────────────────────────────────
# Multi-stage Dockerfile — Healthcare Claim Finalization Agent
# ──────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────
FROM python:3.12-slim

# Non-root user (required by OpenShift SCC)
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY agents/ ./agents/

# OpenShift: ensure /app is writable by any UID in the root group
RUN chown -R 1001:0 /app && chmod -R g=u /app

USER 1001

EXPOSE 8080

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["uvicorn", "agents.api:app", "--host", "0.0.0.0", "--port", "8080"]
