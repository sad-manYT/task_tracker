import pytest

from app.models.enums import TaskStatus
from app.services.task_service import can_change_status


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (TaskStatus.NEW, TaskStatus.IN_PROGRESS),
        (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW),
        (TaskStatus.REVIEW, TaskStatus.DONE),
        (TaskStatus.REVIEW, TaskStatus.IN_PROGRESS),
        (TaskStatus.NEW, TaskStatus.CANCELLED),
        (TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED),
        (TaskStatus.REVIEW, TaskStatus.CANCELLED),
    ],
)
def test_allowed_transitions(current, new):
    assert can_change_status(current, new)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (TaskStatus.NEW, TaskStatus.DONE),
        (TaskStatus.NEW, TaskStatus.REVIEW),
        (TaskStatus.IN_PROGRESS, TaskStatus.DONE),
        (TaskStatus.DONE, TaskStatus.IN_PROGRESS),
        (TaskStatus.DONE, TaskStatus.CANCELLED),
        (TaskStatus.CANCELLED, TaskStatus.NEW),
        (TaskStatus.NEW, TaskStatus.NEW),
    ],
)
def test_forbidden_transitions(current, new):
    assert not can_change_status(current, new)
