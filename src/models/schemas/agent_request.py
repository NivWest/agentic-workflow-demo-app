from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request payload schema for executing an agent workflow."""

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters forwarded to the agent workflow.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Data payload for the agent workflow execution.",
    )
