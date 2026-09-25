from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.agents.orchestrator import AgentOrchestrator
from src.api.dependencies import get_orchestrator
from src.models.schemas.agent_request import AgentRequest
from src.models.schemas.agent_response import AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/{workflow_name}/execute",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AgentResponse,
)
async def execute_agent_workflow(
    workflow_name: str,
    request: AgentRequest,
    orchestrator: Annotated[AgentOrchestrator, Depends(get_orchestrator)],
) -> AgentResponse:
    """Queue an agent workflow execution.

    Args:
        workflow_name: Name of the target agent workflow.
        request: Pydantic request payload containing workflow inputs.
        orchestrator: Injected AgentOrchestrator dependency instance.

    Returns:
        AgentResponse: HTTP 202 Accepted response with task details.
    """
    return await orchestrator.dispatch_async(
        workflow_name=workflow_name,
        request=request,
    )
