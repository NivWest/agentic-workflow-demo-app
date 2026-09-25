from __future__ import annotations

import json
from typing import Any

from google.cloud import tasks_v2
import structlog

from src.core.exceptions import GoogleCloudTasksError

logger = structlog.get_logger()


class GoogleTasksPublisher:
    """Service wrapper for enqueuing agent workflow tasks to Google Cloud Tasks.

    This service encapsulates Google Cloud Tasks SDK operations, formatting
    queue paths and serializing payloads for internal webhook execution.
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        queue_name: str,
        client: tasks_v2.CloudTasksAsyncClient | None = None,
        target_url: str | None = None,
    ) -> None:
        """Initialize the Google Cloud Tasks publisher service.

        Args:
            project_id: GCP project identifier.
            location: GCP region where the Cloud Tasks queue is located.
            queue_name: Name of the Cloud Tasks queue.
            client: Optional CloudTasksAsyncClient instance for dependency injection.
            target_url: Default target URL for internal webhook execution.
        """
        self.project_id = project_id
        self.location = location
        self.queue_name = queue_name
        self.target_url = target_url or "/api/v1/webhook/execute"
        self._client = client or tasks_v2.CloudTasksAsyncClient()

        if client is not None and hasattr(client, "queue_path") and callable(getattr(client, "queue_path")):
            try:
                formatted_path = client.queue_path(project_id, location, queue_name)
                if isinstance(formatted_path, str):
                    self.queue_path = formatted_path
                else:
                    self.queue_path = tasks_v2.CloudTasksAsyncClient.queue_path(
                        project_id, location, queue_name
                    )
            except Exception:
                self.queue_path = tasks_v2.CloudTasksAsyncClient.queue_path(
                    project_id, location, queue_name
                )
        else:
            self.queue_path = tasks_v2.CloudTasksAsyncClient.queue_path(
                project_id, location, queue_name
            )

    async def enqueue(
        self,
        workflow_name: str,
        payload: dict[str, Any],
        target_url: str | None = None,
    ) -> str:
        """Enqueue a payload to the Google Cloud Task queue.

        Args:
            workflow_name: Name of the target workflow to be executed.
            payload: Payload dictionary containing workflow parameters.
            target_url: Optional override for the target webhook URL.

        Returns:
            str: Valid GCP Task ID string upon successful dispatch.

        Raises:
            GoogleCloudTasksError: Re-raised custom exception if dispatch fails.
        """
        url = target_url or self.target_url
        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.error(
                "cloud_tasks_payload_serialization_failed",
                workflow_name=workflow_name,
                error=str(exc),
            )
            raise GoogleCloudTasksError(
                f"Failed to serialize payload to JSON: {exc}"
            ) from exc

        task: dict[str, Any] = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {
                    "Content-Type": "application/json",
                    "X-Workflow-Name": workflow_name,
                },
                "body": payload_bytes,
            }
        }

        try:
            response = await self._client.create_task(
                request={"parent": self.queue_path, "task": task}
            )
        except GoogleCloudTasksError:
            raise
        except Exception as exc:
            logger.error(
                "cloud_tasks_enqueue_failed",
                workflow_name=workflow_name,
                queue_path=self.queue_path,
                error=str(exc),
            )
            raise GoogleCloudTasksError(
                f"Failed to enqueue task in Cloud Tasks: {exc}"
            ) from exc

        task_name = getattr(response, "name", str(response))
        task_id = task_name.split("/")[-1] if "/" in task_name else task_name

        logger.info(
            "cloud_task_enqueued",
            workflow_name=workflow_name,
            task_id=task_id,
            queue_path=self.queue_path,
        )

        return task_id
