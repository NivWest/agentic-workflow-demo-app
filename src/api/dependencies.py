from __future__ import annotations

from src.agents.orchestrator import AgentOrchestrator


def get_orchestrator() -> AgentOrchestrator:
    """Dependency provider that supplies an AgentOrchestrator instance.

    Returns:
        AgentOrchestrator: Configured orchestrator instance.
    """
    return AgentOrchestrator()
