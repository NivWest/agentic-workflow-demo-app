from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from google.cloud import tasks_v2
import pytest

from src.core.exceptions import CloudTasksError, GoogleCloudTasksError, TaskQueueError
from src.services.google_tasks import GoogleTasksPublisher


@pytest.mark.asyncio
async def test_queue_path_formatting() -> None:
    """Test that GoogleTasksPublisher formats the fully qualified queue path correctly."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
    )
    expected_path = "projects/my-project/locations/us-central1/queues/agent-queue"
    assert publisher.queue_path == expected_path


@pytest.mark.asyncio
async def test_init_default_client_instantiation() -> None:
    """Test that CloudTasksAsyncClient is instantiated if no client is provided."""
    with patch("google.cloud.tasks_v2.CloudTasksAsyncClient") as mock_client_cls:
        mock_client_cls.queue_path.side_effect = (
            lambda project, location, queue: f"projects/{project}/locations/{location}/queues/{queue}"
        )
        publisher = GoogleTasksPublisher(
            project_id="my-project",
            location="us-central1",
            queue_name="agent-queue",
        )
        mock_client_cls.assert_called_once()
        assert (
            publisher.queue_path
            == "projects/my-project/locations/us-central1/queues/agent-queue"
        )


@pytest.mark.asyncio
async def test_enqueue_success_full_resource_name() -> None:
    """Test successful task dispatch returning the task ID from a full resource name."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    mock_response = MagicMock()
    mock_response.name = (
        "projects/my-project/locations/us-central1/queues/agent-queue/tasks/7890123"
    )
    mock_client.create_task.return_value = mock_response

    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
    )

    payload = {"job_id": "job-101", "params": {"query": "hello"}}
    task_id = await publisher.enqueue(
        workflow_name="summary_workflow",
        payload=payload,
    )

    assert task_id == "7890123"
    mock_client.create_task.assert_called_once()
    call_kwargs = mock_client.create_task.call_args.kwargs
    request = call_kwargs["request"]

    assert request["parent"] == "projects/my-project/locations/us-central1/queues/agent-queue"
    task = request["task"]
    assert task["http_request"]["url"] == "/api/v1/webhook/execute"
    assert task["http_request"]["headers"]["X-Workflow-Name"] == "summary_workflow"
    assert task["http_request"]["headers"]["Content-Type"] == "application/json"

    # Verify JSON serialization and encoding
    body_bytes = task["http_request"]["body"]
    assert isinstance(body_bytes, bytes)
    assert json.loads(body_bytes.decode("utf-8")) == payload


@pytest.mark.asyncio
async def test_enqueue_success_simple_task_id() -> None:
    """Test successful task dispatch returning a simple task ID."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    mock_response = MagicMock()
    mock_response.name = "task-simple-123"
    mock_client.create_task.return_value = mock_response

    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
    )

    task_id = await publisher.enqueue(
        workflow_name="simple_workflow",
        payload={"data": "test"},
    )

    assert task_id == "task-simple-123"


@pytest.mark.asyncio
async def test_enqueue_custom_target_url() -> None:
    """Test target URL override in enqueue and constructor."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    mock_response = MagicMock()
    mock_response.name = "task-custom-url"
    mock_client.create_task.return_value = mock_response

    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
        target_url="/default/webhook",
    )

    await publisher.enqueue(
        workflow_name="custom_wf",
        payload={"data": "test"},
        target_url="/override/webhook",
    )

    call_kwargs = mock_client.create_task.call_args.kwargs
    task = call_kwargs["request"]["task"]
    assert task["http_request"]["url"] == "/override/webhook"


@pytest.mark.asyncio
async def test_enqueue_raises_custom_exception_on_sdk_error() -> None:
    """Test that GCP SDK errors are caught and re-raised as custom application exceptions."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    mock_client.create_task.side_effect = RuntimeError("GCP Service Unavailable")

    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
    )

    with pytest.raises(GoogleCloudTasksError) as exc_info:
        await publisher.enqueue(
            workflow_name="failing_workflow",
            payload={"test": "data"},
        )

    assert "Failed to enqueue task in Cloud Tasks" in str(exc_info.value)
    # Check aliases
    assert isinstance(exc_info.value, CloudTasksError)
    assert isinstance(exc_info.value, TaskQueueError)


@pytest.mark.asyncio
async def test_enqueue_raises_custom_exception_on_invalid_payload() -> None:
    """Test that payload serialization errors raise GoogleCloudTasksError."""
    mock_client = AsyncMock(spec=tasks_v2.CloudTasksAsyncClient)
    publisher = GoogleTasksPublisher(
        project_id="my-project",
        location="us-central1",
        queue_name="agent-queue",
        client=mock_client,
    )

    # Object that cannot be JSON serialized
    invalid_payload = {"unserializable": object()}

    with pytest.raises(GoogleCloudTasksError) as exc_info:
        await publisher.enqueue(
            workflow_name="invalid_payload_wf",
            payload=invalid_payload,
        )

    assert "Failed to serialize payload to JSON" in str(exc_info.value)
