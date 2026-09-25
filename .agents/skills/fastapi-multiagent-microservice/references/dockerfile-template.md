# Dockerfile Template — Reference

Multi-stage Dockerfile for deploying the FastAPI microservice to Cloud Run.

---

## Template

```dockerfile
# ============================================================
# Stage 1 — Builder: resolve dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time system deps (if needed for compiled wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.lock requirements.lock

# Install into a virtual-env so we can copy it cleanly
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.lock

# ============================================================
# Stage 2 — Runtime: minimal production image
# ============================================================
FROM python:3.11-slim AS runtime

# Non-root user
RUN groupadd --gid 1001 appuser && \
    useradd  --uid 1001 --gid appuser --shell /bin/false appuser

WORKDIR /app

# Copy only the pre-built venv — no compilers in the final image
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY src/ src/

# Drop privileges
USER appuser

# Cloud Run injects $PORT
EXPOSE 8080

CMD ["uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Design Decisions

| Decision               | Rationale                                                                 |
| :--------------------- | :------------------------------------------------------------------------ |
| Multi-stage build      | Separates build deps (gcc) from runtime image → smaller, more secure.    |
| `python:3.11-slim`     | Minimal Debian base; avoids Alpine's musl issues with compiled packages. |
| Virtual-env copy       | Clean boundary; runtime image has no pip or build artifacts.             |
| `appuser` (non-root)   | Principle of least privilege; required for many compliance frameworks.    |
| `--factory` flag       | Uvicorn calls `create_app()` each worker, enabling lifespan per-worker.  |
| No `COPY . .`          | Only `src/` is copied — keeps config, tests, and docs out of the image.  |
| No `ENTRYPOINT` shell  | Direct `CMD` list avoids PID 1 signal-handling issues.                   |

---

## Stateless Container Checklist

- [ ] No local file writes (temp files use `/tmp` only for transient I/O).
- [ ] All persistent state goes to the database, GCS, or an external cache.
- [ ] No in-memory caches that assume instance affinity.
- [ ] Health-check endpoint (`GET /healthz`) has no side effects.
- [ ] Graceful shutdown completes in-flight requests on `SIGTERM`.

---

## `.dockerignore`

```text
.git
.venv
__pycache__
*.pyc
tests/
docs/
*.md
.env
.mypy_cache
.ruff_cache
```
