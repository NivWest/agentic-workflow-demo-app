from __future__ import annotations

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Response schema returned when an agent execution task is queued."""

    job_id: str = Field(
        ...,
        description="Unique identifier for the queued workflow execution job.",
    )
    status: str = Field(
        default="accepted",
        description="Status of the dispatched task.",
    )
    workflow_name: str = Field(
        ...,
        description="Name of the agent workflow to execute.",
    )
