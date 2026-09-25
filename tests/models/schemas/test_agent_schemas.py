from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.models.schemas.agent_schemas import AgentRequest, AgentResponse


class TestAgentRequest:
    """Unit tests for AgentRequest schema."""

    def test_valid_agent_request(self) -> None:
        """Test valid instantiation of AgentRequest."""
        payload: dict[str, Any] = {"text": "Hello world", "max_length": 50}
        request = AgentRequest(
            workflow_name="summarize_text",
            payload=payload,
        )
        assert request.workflow_name == "summarize_text"
        assert request.payload == {"text": "Hello world", "max_length": 50}

    def test_agent_request_missing_workflow_name(self) -> None:
        """Test validation error when workflow_name is missing."""
        data: dict[str, Any] = {"payload": {"key": "value"}}
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("workflow_name",) for err in errors)

    def test_agent_request_missing_payload(self) -> None:
        """Test validation error when payload is missing."""
        data: dict[str, Any] = {"workflow_name": "test_workflow"}
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("payload",) for err in errors)

    def test_agent_request_invalid_payload_type(self) -> None:
        """Test validation error when payload is not a dictionary."""
        data: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "payload": "not-a-dict",
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("payload",) for err in errors)


class TestAgentResponse:
    """Unit tests for AgentResponse schema."""

    def test_valid_agent_response_default_status(self) -> None:
        """Test valid instantiation of AgentResponse with default status."""
        data: dict[str, Any] = {
            "job_id": "job-12345",
            "workflow_name": "summarize_text",
        }
        response = AgentResponse(**data)
        assert response.job_id == "job-12345"
        assert response.workflow_name == "summarize_text"
        assert response.status == "queued"

    def test_valid_agent_response_custom_status(self) -> None:
        """Test valid instantiation of AgentResponse with explicit status."""
        data: dict[str, Any] = {
            "job_id": "job-12345",
            "workflow_name": "summarize_text",
            "status": "processing",
        }
        response = AgentResponse(**data)
        assert response.status == "processing"

    def test_agent_response_missing_job_id(self) -> None:
        """Test validation error when job_id is missing."""
        data: dict[str, Any] = {"workflow_name": "summarize_text"}
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("job_id",) for err in errors)

    def test_agent_response_missing_workflow_name(self) -> None:
        """Test validation error when workflow_name is missing."""
        data: dict[str, Any] = {"job_id": "job-12345"}
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("workflow_name",) for err in errors)
