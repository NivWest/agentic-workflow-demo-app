from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Schema for incoming agent request payload.

    Attributes:
        workflow_name: Name of the workflow to trigger.
        payload: Dictionary containing parameters passed to the workflow.
    """

    workflow_name: str = Field(
        ...,
        description="Name of the agent workflow to trigger.",
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Parameters and input payload forwarded to the agent workflow.",
    )


class AgentResponse(BaseModel):
    """Schema for accepted agent response containing job tracking info.

    Attributes:
        job_id: Unique identifier for the queued job.
        workflow_name: Name of the workflow being executed.
        status: Execution status of the request (defaults to 'queued').
    """

    job_id: str = Field(
        ...,
        description="Unique identifier assigned to the queued workflow execution job.",
    )
    workflow_name: str = Field(
        ...,
        description="Name of the workflow triggered.",
    )
    status: str = Field(
        default="queued",
        description="Status of the request.",
    )
