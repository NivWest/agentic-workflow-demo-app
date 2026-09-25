from __future__ import annotations


class GoogleCloudTasksError(Exception):
    """Raised when an operation on Google Cloud Tasks fails."""


CloudTasksError = GoogleCloudTasksError
TaskQueueError = GoogleCloudTasksError
