import uuid

import pytest

from app.services.tag_service import MAX_TAGS_PER_TASK
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


def create_tag(client, tokens, name):
    return client.post(
        f"{API}/tags", json={"name": name}, headers=auth_header(tokens["access_token"])
    )


def attach(client, tokens, task_id, tag_id):
    return client.post(
        f"{API}/tasks/{task_id}/tags",
        json={"tag_id": tag_id},
        headers=auth_header(tokens["access_token"]),
    )


def test_create_tag_normalizes_name(client, owner):
    response = create_tag(client, owner, "  Срочно ")

    assert response.status_code == 201
    assert response.json()["name"] == "срочно"


def test_duplicate_tag_is_rejected(client, owner):
    create_tag(client, owner, "срочно")

    response = create_tag(client, owner, "СРОЧНО")

    assert response.status_code == 409


@pytest.mark.parametrize("name", ["", "   ", "a" * 51, "<script>", "bad\u0000"])
def test_invalid_tag_name_is_rejected(client, owner, name):
    response = create_tag(client, owner, name)

    assert response.status_code == 422


def test_tags_require_authentication(client):
    response = client.get(f"{API}/tags")

    assert response.status_code == 401


def test_list_and_search_tags(client, owner):
    for name in ["срочно", "дом", "работа"]:
        create_tag(client, owner, name)

    all_tags = client.get(f"{API}/tags", headers=auth_header(owner["access_token"])).json()
    found = client.get(
        f"{API}/tags", params={"search": "СРОЧ"}, headers=auth_header(owner["access_token"])
    ).json()

    assert [tag["name"] for tag in all_tags["items"]] == ["дом", "работа", "срочно"]
    assert found["total"] == 1


def test_attach_tag_to_task(client, owner, task):
    tag = create_tag(client, owner, "срочно").json()

    response = attach(client, owner, task["id"], tag["id"])

    assert response.status_code == 200
    assert response.json()["tags"] == [tag]


def test_tag_cannot_be_attached_twice(client, owner, task):
    tag = create_tag(client, owner, "срочно").json()
    attach(client, owner, task["id"], tag["id"])

    response = attach(client, owner, task["id"], tag["id"])

    assert response.status_code == 409


def test_unknown_tag_cannot_be_attached(client, owner, task):
    response = attach(client, owner, task["id"], str(uuid.uuid4()))

    assert response.status_code == 404


def test_tag_limit_per_task(client, owner, task):
    for number in range(MAX_TAGS_PER_TASK):
        tag = create_tag(client, owner, f"тег {number}").json()
        attach(client, owner, task["id"], tag["id"])
    extra = create_tag(client, owner, "лишний").json()

    response = attach(client, owner, task["id"], extra["id"])

    assert response.status_code == 400


def test_viewer_cannot_attach_tags(client, owner, project, task):
    viewer = create_user(client, "viewer")
    add_member(client, owner, project["id"], "viewer", "viewer")
    tag = create_tag(client, viewer, "срочно").json()

    response = attach(client, viewer, task["id"], tag["id"])

    assert response.status_code == 403


def test_stranger_cannot_attach_tags(client, owner, task):
    stranger = create_user(client, "stranger")
    tag = create_tag(client, stranger, "срочно").json()

    response = attach(client, stranger, task["id"], tag["id"])

    assert response.status_code == 404


def test_detach_tag(client, owner, task):
    tag = create_tag(client, owner, "срочно").json()
    attach(client, owner, task["id"], tag["id"])

    response = client.delete(
        f"{API}/tasks/{task['id']}/tags/{tag['id']}", headers=auth_header(owner["access_token"])
    )
    after = client.get(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))

    assert response.status_code == 204
    assert after.json()["tags"] == []


def test_detach_not_attached_tag_returns_not_found(client, owner, task):
    tag = create_tag(client, owner, "срочно").json()

    response = client.delete(
        f"{API}/tasks/{task['id']}/tags/{tag['id']}", headers=auth_header(owner["access_token"])
    )

    assert response.status_code == 404


def test_filter_tasks_by_tag(client, owner, project, task):
    tag = create_tag(client, owner, "срочно").json()
    attach(client, owner, task["id"], tag["id"])
    client.post(
        f"{API}/tasks",
        json={"project_id": project["id"], "title": "Без тега"},
        headers=auth_header(owner["access_token"]),
    )

    response = client.get(
        f"{API}/tasks", params={"tag_id": tag["id"]}, headers=auth_header(owner["access_token"])
    ).json()

    assert response["total"] == 1
    assert response["items"][0]["id"] == task["id"]


def test_deleting_task_keeps_tag(client, owner, task):
    tag = create_tag(client, owner, "срочно").json()
    attach(client, owner, task["id"], tag["id"])

    client.delete(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))
    tags = client.get(f"{API}/tags", headers=auth_header(owner["access_token"])).json()

    assert tags["total"] == 1
