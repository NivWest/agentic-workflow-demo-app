---
name: fastapi-multiagent-microservice
description: >-
  Architecture patterns and best practices for building scalable, multi-agent
  microservices with FastAPI, Python 3.11+, Domain-Driven Design (DDD), and
  Hexagonal Architecture on Google Cloud Platform (GCP). Use when the user asks
  to scaffold, write, refactor, or review code for a FastAPI multi-agent
  microservice. Also use when discussions involve async dispatch via Cloud Tasks,
  agent orchestration registries, OpenTelemetry observability, or containerized
  Cloud Run deployments. Do NOT use for simple single-endpoint Flask/Django
  apps, front-end projects, or non-Python microservices.
---

# FastAPI Multi-Agent Microservice — Architecture Skill

This skill enforces a production-grade architecture for Python microservices
that orchestrate multiple AI agent workflows behind a FastAPI transport layer,
deployed to Google Cloud Run.

## When to Activate

Activate this skill when:

- Scaffolding a new FastAPI project that orchestrates agent workflows.
- Adding, refactoring, or reviewing code in a project that follows the
  directory structure described below.
- Designing async dispatch patterns (Cloud Tasks, webhooks).
- Configuring observability (OpenTelemetry + structlog) for agent services.
- Writing or reviewing Dockerfiles for Cloud Run deployment.
- Implementing dependency injection wiring for testable services.

---

## 1. Canonical Directory Structure

All code **must** conform to this hybrid feature/layer layout. Do not deviate.

```text
├── build/                     # Multi-stage Dockerfiles
├── src/
│   ├── api/                   # Transport Layer
│   │   ├── v1/                # Versioned endpoint routers
│   │   └── dependencies.py    # FastAPI Depends() wiring
│   ├── agents/                # Domain Logic (Agentic Workflows)
│   │   ├── orchestrator.py    # Registry, state machine, dispatch
│   │   ├── workflows/         # One module per agent workflow
│   │   └── tools/             # Action tools injected into agents
│   ├── services/              # External Integrations Layer
│   │   ├── gcs_storage.py     # Google Cloud Storage wrappers
│   │   ├── google_tasks.py    # Cloud Tasks queue publisher
│   │   └── token_client.py    # External OAuth/JWT acquisition
│   ├── repositories/          # Data Access Layer
│   │   └── state_repo.py      # Agent state persistence
│   ├── core/                  # App-wide Configuration & Infra
│   │   ├── config.py          # Pydantic v2 BaseSettings
│   │   ├── exceptions.py      # Global exception handlers
│   │   ├── lifespan.py        # Startup/shutdown context manager
│   │   └── telemetry.py       # OpenTelemetry + structlog setup
│   ├── models/
│   │   ├── domain/            # Internal business logic models
│   │   └── schemas/           # Pydantic request/response DTOs
│   └── main.py                # Application factory
└── tests/                     # Mirror src/ layout
```

### Boundary Rules (Hard Constraints)

| Source Layer       | May Depend On                               | Must NOT Depend On          |
| :----------------- | :------------------------------------------ | :-------------------------- |
| `api/`             | `agents/orchestrator`, `models/schemas`      | `services/`, `repositories/` |
| `agents/`          | `services/`, `repositories/`, `models/domain`| `api/`                      |
| `services/`        | `core/config`, external SDKs                 | `agents/`, `api/`           |
| `repositories/`    | `core/config`, ORM/driver                    | `agents/`, `api/`, `services/` |

> **Violation check:** Before generating any import statement, verify it does
> not cross a forbidden boundary.

---

## 2. API & Async Dispatch Rules

1. **Routers are traffic cops.** Endpoints parse HTTP, validate via Pydantic
   schemas, and delegate to the `AgentOrchestrator`. They contain zero
   business logic.

2. **Always return HTTP 202 Accepted.** When an agent execution is requested,
   queue the work via Cloud Tasks (or `BackgroundTasks` in dev) and return a
   `job_id` immediately.

3. **Registry pattern for agents.** `AgentOrchestrator` discovers workflow
   classes automatically. Adding a new agent = adding a file in
   `src/agents/workflows/`. Zero router changes.

4. **Webhook execution.** A secured internal endpoint
   (`POST /webhook/execute`) is the Cloud Tasks target. It deserializes the
   payload, resolves the agent from the registry, and executes the workflow.

> For code examples, see [api-patterns.md](./references/api-patterns.md).

---

## 3. Dependency Injection

- All DI wiring lives in `src/api/dependencies.py`.
- Use `Depends()` exclusively — no module-level singletons.
- Services accept clients/config via `__init__` for full testability through
  `app.dependency_overrides`.
- Shared async resources (e.g., `httpx.AsyncClient`) are created in lifespan
  and stored in `app.state`.

---

## 4. Coding Standards (Non-Negotiable)

| Topic            | Requirement                                                                 |
| :--------------- | :-------------------------------------------------------------------------- |
| **Lifespan**     | Use `@asynccontextmanager` in `core/lifespan.py`. Never `@app.on_event()`. |
| **Config**       | `BaseSettings` with `Field(default=..., description=...)`. Fail fast on boot. |
| **I/O**          | 100% async: `httpx`, `asyncpg`, async GCP SDKs. No blocking in async def.  |
| **Type hints**   | Full annotations. Must pass `mypy --strict`.                               |
| **Logging**      | `structlog` with JSON output. Never `import logging`.                      |
| **Tracing**      | Bind `trace_id` + `job_id` into structlog context per request.             |
| **OTel**         | Auto-instrument FastAPI and httpx. Export to Cloud Trace.                   |

> For detailed telemetry setup, see [telemetry-setup.md](./references/telemetry-setup.md).

---

## 5. Containerization

- **Multi-stage Dockerfile** based on `python:3.11-slim`.
- Stage 1: install dependencies. Stage 2: copy app, run as `appuser` (non-root).
- Container must be **stateless**. All state goes to the database or GCS.

> For a Dockerfile template, see [dockerfile-template.md](./references/dockerfile-template.md).

---

## 6. Validation Checklist

Before finalizing any generated code, verify every item:

- [ ] No import crosses a forbidden layer boundary.
- [ ] No endpoint contains business logic beyond validation and dispatch.
- [ ] Agent execution is async-dispatched (HTTP 202 + job_id).
- [ ] New agents require zero changes to routers or orchestrator.
- [ ] All I/O is async — no blocking calls in `async def`.
- [ ] `structlog` is used (not `logging`). `trace_id` and `job_id` are bound.
- [ ] `BaseSettings` loads config; startup fails fast on missing vars.
- [ ] Lifespan uses `@asynccontextmanager`, not `on_event`.
- [ ] Dockerfile is multi-stage, non-root, stateless.
- [ ] All functions are fully type-hinted (`mypy --strict` clean).
