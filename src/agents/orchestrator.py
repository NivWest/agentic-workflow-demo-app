from __future__ import annotations

from uuid import uuid4

import structlog

from src.models.schemas.agent_request import AgentRequest
from src.models.schemas.agent_response import AgentResponse

logger = structlog.get_logger()


class AgentOrchestrator:
    """Orchestrates agent workflow discovery and asynchronous task dispatch."""

    async def dispatch_async(
        self,
        workflow_name: str,
        request: AgentRequest,
    ) -> AgentResponse:
        """Asynchronously dispatches an agent workflow task.

        Args:
            workflow_name: The name of the target workflow.
            request: The request payload and parameters for execution.

        Returns:
            AgentResponse: Response containing job ID and queue status.
        """
        job_id = str(uuid4())
        logger.info(
            "dispatching_agent_workflow",
            workflow_name=workflow_name,
            job_id=job_id,
            parameters=request.parameters,
        )
        return AgentResponse(
            job_id=job_id,
            status="accepted",
            workflow_name=workflow_name,
        )
