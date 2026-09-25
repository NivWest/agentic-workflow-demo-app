# API & Dispatch Patterns — Reference

Detailed code examples for the Transport Layer, async dispatch, the agent
registry, and the webhook execution endpoint.

---

## Router (Transport Layer)

Routers are thin. They validate, dispatch, and return.

```python
# src/api/v1/agents.py
from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from src.agents.orchestrator import AgentOrchestrator
from src.api.dependencies import get_orchestrator
from src.models.schemas.agent_request import AgentRunRequest
from src.models.schemas.agent_response import AgentAcceptedResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AgentAcceptedResponse,
)
async def request_agent_run(
    payload: AgentRunRequest,
    orchestrator: Annotated[AgentOrchestrator, Depends(get_orchestrator)],
) -> AgentAcceptedResponse:
    """Queue an agent workflow for async execution.

    Returns immediately with a ``job_id`` the caller can poll.
    """
    job_id = str(uuid4())
    await orchestrator.dispatch(
        agent_name=payload.agent_name,
        job_id=job_id,
        params=payload.params,
    )
    return AgentAcceptedResponse(job_id=job_id, status="queued")
```

### Key points

- The router never imports anything from `services/` or `repositories/`.
- The only injected dependency is `AgentOrchestrator`.
- The response is HTTP 202 with a `job_id` — never a synchronous result.

---

## Dependency Injection Wiring

```python
# src/api/dependencies.py
from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.orchestrator import AgentOrchestrator
from src.repositories.state_repo import StateRepository
from src.services.google_tasks import GoogleTasksPublisher


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session from the engine on ``app.state``."""
    async with request.app.state.async_session_factory() as session:
        yield session


def get_state_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StateRepository:
    return StateRepository(session=session)


def get_tasks_publisher(request: Request) -> GoogleTasksPublisher:
    return GoogleTasksPublisher(
        client=request.app.state.tasks_client,
        config=request.app.state.settings,
    )


def get_orchestrator(
    publisher: Annotated[GoogleTasksPublisher, Depends(get_tasks_publisher)],
    state_repo: Annotated[StateRepository, Depends(get_state_repo)],
) -> AgentOrchestrator:
    return AgentOrchestrator(
        publisher=publisher,
        state_repo=state_repo,
    )
```

---

## Agent Orchestrator (Registry Pattern)

```python
# src/agents/orchestrator.py
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

import structlog

from src.agents.workflows import base
from src.services.google_tasks import GoogleTasksPublisher
from src.repositories.state_repo import StateRepository

logger = structlog.get_logger()


class AgentOrchestrator:
    """Discovers and dispatches agent workflows via a dynamic registry."""

    def __init__(
        self,
        publisher: GoogleTasksPublisher,
        state_repo: StateRepository,
    ) -> None:
        self._publisher = publisher
        self._state_repo = state_repo
        self._registry: dict[str, type[base.BaseAgentWorkflow]] = {}
        self._discover_agents()

    # ── Registry ────────────────────────────────────────────────────
    def _discover_agents(self) -> None:
        """Auto-discover all ``BaseAgentWorkflow`` subclasses in workflows/."""
        import src.agents.workflows as pkg

        for module_info in pkgutil.walk_packages(
            pkg.__path__,
            prefix=f"{pkg.__name__}.",
        ):
            module = importlib.import_module(module_info.name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base.BaseAgentWorkflow)
                    and attr is not base.BaseAgentWorkflow
                ):
                    self._registry[attr.name] = attr
                    logger.info("agent_registered", agent=attr.name)

    # ── Dispatch ────────────────────────────────────────────────────
    async def dispatch(
        self,
        agent_name: str,
        job_id: str,
        params: dict[str, Any],
    ) -> None:
        if agent_name not in self._registry:
            raise ValueError(f"Unknown agent: {agent_name}")

        await self._state_repo.create_job(job_id=job_id, agent=agent_name)
        await self._publisher.enqueue(
            agent_name=agent_name,
            job_id=job_id,
            payload=params,
        )
        logger.info("agent_dispatched", agent=agent_name, job_id=job_id)

    # ── Execution (called from webhook) ─────────────────────────────
    async def execute(
        self,
        agent_name: str,
        job_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        agent_cls = self._registry[agent_name]
        agent = agent_cls()
        result = await agent.run(job_id=job_id, params=params)
        await self._state_repo.complete_job(job_id=job_id, result=result)
        return result
```

---

## Webhook Endpoint (Cloud Tasks Target)

```python
# src/api/v1/webhook.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.agents.orchestrator import AgentOrchestrator
from src.api.dependencies import get_orchestrator
from src.models.schemas.webhook_payload import WebhookExecutePayload

router = APIRouter(prefix="/webhook", tags=["internal"])


@router.post("/execute", status_code=status.HTTP_200_OK)
async def execute_agent(
    payload: WebhookExecutePayload,
    orchestrator: Annotated[AgentOrchestrator, Depends(get_orchestrator)],
    x_cloudtasks_queuename: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Secured endpoint invoked by Google Cloud Tasks.

    In production, validate the ``X-CloudTasks-*`` headers or use
    IAM-authenticated HTTP targets.
    """
    if x_cloudtasks_queuename is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct invocation not allowed.",
        )

    result = await orchestrator.execute(
        agent_name=payload.agent_name,
        job_id=payload.job_id,
        params=payload.params,
    )
    return {"status": "completed", "job_id": payload.job_id}
```

---

## Pydantic Schemas

```python
# src/models/schemas/agent_request.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    agent_name: str = Field(..., description="Registry key of the target agent")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary parameters forwarded to the agent",
    )


# src/models/schemas/agent_response.py
class AgentAcceptedResponse(BaseModel):
    job_id: str
    status: str = "queued"


# src/models/schemas/webhook_payload.py
class WebhookExecutePayload(BaseModel):
    agent_name: str
    job_id: str
    params: dict[str, Any] = Field(default_factory=dict)
```

---

## Base Agent Workflow

```python
# src/agents/workflows/base.py
from __future__ import annotations

import abc
from typing import Any


class BaseAgentWorkflow(abc.ABC):
    """Abstract base for all agent workflows.

    Subclasses **must** set a unique ``name`` class attribute and implement
    ``run()``.
    """

    name: str  # class-level registry key

    @abc.abstractmethod
    async def run(
        self,
        job_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the agent workflow and return a result dict."""
        ...
```

### Adding a New Agent (Zero-Change Example)

```python
# src/agents/workflows/summarizer.py
from __future__ import annotations

from typing import Any

from src.agents.workflows.base import BaseAgentWorkflow


class SummarizerAgent(BaseAgentWorkflow):
    name = "summarizer"

    async def run(
        self, job_id: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        text = params["text"]
        # ... ADK / LLM logic ...
        return {"summary": text[:100]}
```

Drop this file into `src/agents/workflows/` and the orchestrator discovers it
automatically. No router or config changes needed.
