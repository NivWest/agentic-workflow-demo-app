from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.dependencies import get_orchestrator
from src.main import app
from src.models.schemas.agent_response import AgentResponse


@pytest.fixture
def mock_orchestrator() -> AsyncMock:
    """Fixture providing a mocked AgentOrchestrator."""
    mock = AsyncMock()
    mock.dispatch_async.return_value = AgentResponse(
        job_id="test-job-456",
        status="accepted",
        workflow_name="summarizer",
    )
    return mock


def test_execute_agent_workflow_success(mock_orchestrator: AsyncMock) -> None:
    """Verify POST /agents/{workflow_name}/execute returns HTTP 202 Accepted.

    Args:
        mock_orchestrator: Mocked AgentOrchestrator instance.
    """
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

    client = TestClient(app)
    response = client.post(
        "/agents/summarizer/execute",
        json={
            "parameters": {"max_length": 100},
            "payload": {"text": "Hello world"},
        },
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["job_id"] == "test-job-456"
    assert data["status"] == "accepted"
    assert data["workflow_name"] == "summarizer"

    mock_orchestrator.dispatch_async.assert_awaited_once()

    app.dependency_overrides.clear()
