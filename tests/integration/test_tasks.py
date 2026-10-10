import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Category
from tests.utils import API, add_member, auth_header, create_project, create_user


@pytest.fixture
def owner(client):
    return create_user(client, "owner")


@pytest.fixture
def project(client, owner):
    return create_project(client, owner)


def create_task(client, tokens, project_id, **fields):
    payload = {"project_id": project_id, "title": "Задача", **fields}
    return client.post(f"{API}/tasks", json=payload, headers=auth_header(tokens["access_token"]))


def member(client, owner, project, name, role):
    tokens = create_user(client, name)
    user_id = add_member(client, owner, project["id"], name, role).json()["user_id"]
    return tokens, user_id


def future(days=7):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def set_status(client, tokens, task_id, status):
    return client.patch(
        f"{API}/tasks/{task_id}/status",
        json={"status": status},
        headers=auth_header(tokens["access_token"]),
    )


def list_tasks(client, tokens, **params):
    return client.get(f"{API}/tasks", params=params, headers=auth_header(tokens["access_token"]))


def test_create_task(client, owner, project):
    response = create_task(client, owner, project["id"], priority="high", deadline=future())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["priority"] == "high"
    assert body["creator_id"] == project["owner_id"]


def test_viewer_cannot_create_task(client, owner, project):
    viewer, _ = member(client, owner, project, "viewer", "viewer")

    response = create_task(client, viewer, project["id"])

    assert response.status_code == 403


def test_stranger_cannot_create_task_in_foreign_project(client, project):
    stranger = create_user(client, "stranger")

    response = create_task(client, stranger, project["id"])

    assert response.status_code == 404


@pytest.mark.parametrize(
    "deadline",
    [
        "2020-01-01T00:00:00Z",
        "2030-01-01T00:00:00",
        "9999-12-31T23:59:59-10:00",
        "not-a-date",
    ],
)
def test_invalid_deadline_is_rejected(client, owner, project, deadline):
    response = create_task(client, owner, project["id"], deadline=deadline)

    assert response.status_code == 422


def test_assignee_must_be_project_member(client, owner, project):
    stranger = create_user(client, "stranger")
    stranger_id = client.get(
        f"{API}/users/me", headers=auth_header(stranger["access_token"])
    ).json()["id"]

    response = create_task(client, owner, project["id"], assignee_id=stranger_id)

    assert response.status_code == 400


def test_category_must_belong_to_project(client, owner, project, db_session):
    other_project = create_project(client, owner, title="Другой проект")
    category = Category(project_id=uuid.UUID(other_project["id"]), name="Чужая")
    db_session.add(category)
    db_session.commit()

    response = create_task(client, owner, project["id"], category_id=str(category.id))

    assert response.status_code == 400


def test_task_is_hidden_from_stranger(client, owner, project):
    task = create_task(client, owner, project["id"]).json()
    stranger = create_user(client, "stranger")

    response = client.get(
        f"{API}/tasks/{task['id']}", headers=auth_header(stranger["access_token"])
    )

    assert response.status_code == 404


def test_editor_can_update_task(client, owner, project):
    task = create_task(client, owner, project["id"]).json()
    editor, _ = member(client, owner, project, "editor", "editor")

    response = client.patch(
        f"{API}/tasks/{task['id']}",
        json={"title": "Обновлено", "deadline": None},
        headers=auth_header(editor["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Обновлено"


def test_viewer_cannot_update_task(client, owner, project):
    task = create_task(client, owner, project["id"]).json()
    viewer, _ = member(client, owner, project, "viewer", "viewer")

    response = client.patch(
        f"{API}/tasks/{task['id']}",
        json={"title": "Взлом"},
        headers=auth_header(viewer["access_token"]),
    )

    assert response.status_code == 403


def test_task_title_cannot_be_null(client, owner, project):
    task = create_task(client, owner, project["id"]).json()

    response = client.patch(
        f"{API}/tasks/{task['id']}",
        json={"title": None},
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 422


def test_delete_task(client, owner, project):
    task = create_task(client, owner, project["id"]).json()

    response = client.delete(
        f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"])
    )
    after = client.get(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))

    assert response.status_code == 204
    assert after.status_code == 404


def test_deleting_project_deletes_its_tasks(client, owner, project):
    task = create_task(client, owner, project["id"]).json()

    client.delete(f"{API}/projects/{project['id']}", headers=auth_header(owner["access_token"]))
    response = client.get(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))

    assert response.status_code == 404


def test_list_contains_only_accessible_tasks(client, owner, project):
    create_task(client, owner, project["id"])
    stranger = create_user(client, "stranger")
    foreign_project = create_project(client, stranger)
    create_task(client, stranger, foreign_project["id"])

    response = list_tasks(client, owner)

    assert response.json()["total"] == 1


def test_list_filters_by_status_and_priority(client, owner, project):
    task = create_task(client, owner, project["id"], priority="high").json()
    create_task(client, owner, project["id"], priority="low")
    set_status(client, owner, task["id"], "in_progress")

    by_status = list_tasks(client, owner, status="in_progress").json()
    by_priority = list_tasks(client, owner, priority="low").json()

    assert [item["id"] for item in by_status["items"]] == [task["id"]]
    assert by_priority["total"] == 1


def test_list_search_is_case_insensitive_and_escaped(client, owner, project):
    create_task(client, owner, project["id"], title="Купить МОЛОКО")
    create_task(client, owner, project["id"], title="Скидка 50%")
    create_task(client, owner, project["id"], title="Скидка 500")

    by_word = list_tasks(client, owner, search="молоко").json()
    by_percent = list_tasks(client, owner, search="50%").json()

    assert by_word["total"] == 1
    assert by_percent["total"] == 1


def test_list_sorts_by_priority(client, owner, project):
    for priority in ["low", "critical", "medium", "high"]:
        create_task(client, owner, project["id"], title=priority, priority=priority)

    response = list_tasks(client, owner, sort_by="priority", order="desc").json()

    assert [item["priority"] for item in response["items"]] == [
        "critical",
        "high",
        "medium",
        "low",
    ]


def test_list_pagination(client, owner, project):
    for number in range(3):
        create_task(client, owner, project["id"], title=f"Задача {number}")

    response = list_tasks(client, owner, limit=2, offset=2).json()

    assert response["total"] == 3
    assert len(response["items"]) == 1


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"sort_by": "password_hash"}, {"status": "unknown"}],
)
def test_list_rejects_invalid_parameters(client, owner, params):
    response = list_tasks(client, owner, **params)

    assert response.status_code == 422


def test_full_status_workflow(client, owner, project):
    task = create_task(client, owner, project["id"]).json()

    statuses = [
        set_status(client, owner, task["id"], status).json()["status"]
        for status in ["in_progress", "review", "done"]
    ]

    assert statuses == ["in_progress", "review", "done"]


def test_invalid_status_transition_is_rejected(client, owner, project):
    task = create_task(client, owner, project["id"]).json()

    response = set_status(client, owner, task["id"], "done")

    assert response.status_code == 400


def test_done_task_cannot_be_reopened(client, owner, project):
    task = create_task(client, owner, project["id"]).json()
    for status in ["in_progress", "review", "done"]:
        set_status(client, owner, task["id"], status)

    response = set_status(client, owner, task["id"], "in_progress")

    assert response.status_code == 400


def test_assigned_viewer_can_change_status(client, owner, project):
    viewer, viewer_id = member(client, owner, project, "viewer", "viewer")
    task = create_task(client, owner, project["id"], assignee_id=viewer_id).json()

    response = set_status(client, viewer, task["id"], "in_progress")

    assert response.status_code == 200


def test_not_assigned_viewer_cannot_change_status(client, owner, project):
    viewer, _ = member(client, owner, project, "viewer", "viewer")
    task = create_task(client, owner, project["id"]).json()

    response = set_status(client, viewer, task["id"], "in_progress")

    assert response.status_code == 403


def test_assign_and_unassign_task(client, owner, project):
    _, editor_id = member(client, owner, project, "editor", "editor")
    task = create_task(client, owner, project["id"]).json()
    url = f"{API}/tasks/{task['id']}/assignee"
    headers = auth_header(owner["access_token"])

    assigned = client.patch(url, json={"assignee_id": editor_id}, headers=headers)
    unassigned = client.patch(url, json={"assignee_id": None}, headers=headers)

    assert assigned.json()["assignee_id"] == editor_id
    assert unassigned.json()["assignee_id"] is None


def test_removed_member_is_unassigned_from_tasks(client, owner, project):
    _, editor_id = member(client, owner, project, "editor", "editor")
    task = create_task(client, owner, project["id"], assignee_id=editor_id).json()

    client.delete(
        f"{API}/projects/{project['id']}/members/{editor_id}",
        headers=auth_header(owner["access_token"]),
    )
    response = client.get(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))

    assert response.json()["assignee_id"] is None
