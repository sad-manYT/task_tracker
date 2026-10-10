import uuid

import pytest

from tests.utils import API, add_member, auth_header, create_project, create_user


@pytest.fixture
def owner(client):
    return create_user(client, "owner")


@pytest.fixture
def project(client, owner):
    return create_project(client, owner)


@pytest.fixture
def task(client, owner, project):
    response = client.post(
        f"{API}/tasks",
        json={"project_id": project["id"], "title": "Задача"},
        headers=auth_header(owner["access_token"]),
    )
    return response.json()


@pytest.fixture
def viewer(client, owner, project):
    tokens = create_user(client, "viewer")
    add_member(client, owner, project["id"], "viewer", "viewer")
    return tokens


def add_comment(client, tokens, task_id, body="Комментарий"):
    return client.post(
        f"{API}/tasks/{task_id}/comments",
        json={"body": body},
        headers=auth_header(tokens["access_token"]),
    )


def delete_comment(client, tokens, comment_id):
    return client.delete(
        f"{API}/comments/{comment_id}", headers=auth_header(tokens["access_token"])
    )


def test_add_comment(client, owner, task):
    response = add_comment(client, owner, task["id"], body="  Готово наполовину  ")

    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "Готово наполовину"
    assert body["author_username"] == "owner"


def test_viewer_can_comment(client, viewer, task):
    response = add_comment(client, viewer, task["id"])

    assert response.status_code == 201


def test_stranger_cannot_comment_or_read(client, task):
    stranger = create_user(client, "stranger")

    created = add_comment(client, stranger, task["id"])
    listed = client.get(
        f"{API}/tasks/{task['id']}/comments", headers=auth_header(stranger["access_token"])
    )

    assert created.status_code == 404
    assert listed.status_code == 404


@pytest.mark.parametrize("body", ["", "   ", "a" * 2001, "bad\u0000text"])
def test_invalid_comment_is_rejected(client, owner, task, body):
    response = add_comment(client, owner, task["id"], body=body)

    assert response.status_code == 422


def test_comment_is_stored_as_plain_text(client, owner, task):
    payload = "<script>alert(1)</script>"

    response = add_comment(client, owner, task["id"], body=payload)

    assert response.json()["body"] == payload
    assert response.headers["content-type"] == "application/json"


def test_list_comments_with_pagination(client, owner, viewer, task):
    add_comment(client, owner, task["id"], body="Первый")
    add_comment(client, viewer, task["id"], body="Второй")
    add_comment(client, owner, task["id"], body="Третий")

    response = client.get(
        f"{API}/tasks/{task['id']}/comments",
        params={"limit": 2},
        headers=auth_header(owner["access_token"]),
    ).json()

    assert response["total"] == 3
    assert len(response["items"]) == 2


def test_author_can_delete_own_comment(client, viewer, task):
    comment = add_comment(client, viewer, task["id"]).json()

    response = delete_comment(client, viewer, comment["id"])

    assert response.status_code == 204


def test_owner_can_delete_any_comment(client, owner, viewer, task):
    comment = add_comment(client, viewer, task["id"]).json()

    response = delete_comment(client, owner, comment["id"])

    assert response.status_code == 204


def test_editor_cannot_delete_other_comments(client, owner, project, task):
    editor = create_user(client, "editor")
    add_member(client, owner, project["id"], "editor", "editor")
    comment = add_comment(client, owner, task["id"]).json()

    response = delete_comment(client, editor, comment["id"])

    assert response.status_code == 403


def test_stranger_cannot_delete_comment(client, owner, task):
    comment = add_comment(client, owner, task["id"]).json()
    stranger = create_user(client, "stranger")

    response = delete_comment(client, stranger, comment["id"])

    assert response.status_code == 404


def test_unknown_comment_returns_not_found(client, owner):
    response = delete_comment(client, owner, uuid.uuid4())

    assert response.status_code == 404


def test_deleting_task_deletes_comments(client, owner, task):
    comment = add_comment(client, owner, task["id"]).json()

    client.delete(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))
    response = delete_comment(client, owner, comment["id"])

    assert response.status_code == 404
