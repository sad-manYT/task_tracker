import uuid

import pytest

from tests.utils import API, add_member, auth_header, create_project, create_user


@pytest.fixture
def owner(client):
    return create_user(client, "owner")


@pytest.fixture
def stranger(client):
    return create_user(client, "stranger")


@pytest.fixture
def project(client, owner):
    return create_project(client, owner)


def test_create_project_makes_creator_owner(client, owner):
    response = client.post(
        f"{API}/projects",
        json={"title": "  Курсовая  ", "description": "Описание"},
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Курсовая"
    assert body["my_role"] == "owner"


def test_create_project_requires_authentication(client):
    response = client.post(f"{API}/projects", json={"title": "Проект"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "a" * 201},
        {"title": "bad\u0000title"},
        {"title": "Проект", "owner_id": str(uuid.uuid4())},
    ],
)
def test_create_project_rejects_invalid_data(client, owner, payload):
    response = client.post(
        f"{API}/projects", json=payload, headers=auth_header(owner["access_token"])
    )

    assert response.status_code == 422


def test_list_contains_only_own_projects(client, owner, stranger, project):
    create_project(client, stranger, title="Чужой проект")

    response = client.get(f"{API}/projects", headers=auth_header(owner["access_token"]))

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 1
    assert body["items"][0]["id"] == project["id"]


def test_foreign_project_is_hidden(client, stranger, project):
    response = client.get(
        f"{API}/projects/{project['id']}", headers=auth_header(stranger["access_token"])
    )

    assert response.status_code == 404


def test_unknown_project_returns_not_found(client, owner):
    response = client.get(
        f"{API}/projects/{uuid.uuid4()}", headers=auth_header(owner["access_token"])
    )

    assert response.status_code == 404


def test_invalid_project_id_is_rejected(client, owner):
    response = client.get(f"{API}/projects/not-a-uuid", headers=auth_header(owner["access_token"]))

    assert response.status_code == 422


def test_owner_can_update_project(client, owner, project):
    response = client.patch(
        f"{API}/projects/{project['id']}",
        json={"title": "Новое название", "description": None},
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Новое название"
    assert response.json()["description"] is None


def test_project_title_cannot_be_null(client, owner, project):
    response = client.patch(
        f"{API}/projects/{project['id']}",
        json={"title": None},
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 422


def test_editor_cannot_update_or_delete_project(client, owner, project):
    editor = create_user(client, "editor")
    add_member(client, owner, project["id"], "editor", "editor")

    update = client.patch(
        f"{API}/projects/{project['id']}",
        json={"title": "Взлом"},
        headers=auth_header(editor["access_token"]),
    )
    delete = client.delete(
        f"{API}/projects/{project['id']}", headers=auth_header(editor["access_token"])
    )

    assert update.status_code == 403
    assert delete.status_code == 403


def test_owner_can_delete_project(client, owner, project):
    response = client.delete(
        f"{API}/projects/{project['id']}", headers=auth_header(owner["access_token"])
    )
    after = client.get(
        f"{API}/projects/{project['id']}", headers=auth_header(owner["access_token"])
    )

    assert response.status_code == 204
    assert after.status_code == 404


def test_owner_can_add_member(client, owner, project):
    viewer = create_user(client, "viewer")

    response = add_member(client, owner, project["id"], "viewer", "viewer")
    shared = client.get(
        f"{API}/projects/{project['id']}", headers=auth_header(viewer["access_token"])
    )

    assert response.status_code == 201
    assert shared.status_code == 200
    assert shared.json()["my_role"] == "viewer"


def test_members_list_contains_owner_and_member(client, owner, project):
    create_user(client, "viewer")
    add_member(client, owner, project["id"], "viewer", "viewer")

    response = client.get(
        f"{API}/projects/{project['id']}/members", headers=auth_header(owner["access_token"])
    )

    roles = {member["username"]: member["role"] for member in response.json()}
    assert roles == {"owner": "owner", "viewer": "viewer"}


def test_member_cannot_be_added_twice(client, owner, project):
    create_user(client, "viewer")
    add_member(client, owner, project["id"], "viewer", "viewer")

    response = add_member(client, owner, project["id"], "viewer", "editor")

    assert response.status_code == 409


def test_unknown_user_cannot_be_added(client, owner, project):
    response = add_member(client, owner, project["id"], "nobody", "viewer")

    assert response.status_code == 404


def test_second_owner_cannot_be_added(client, owner, project):
    create_user(client, "viewer")

    response = add_member(client, owner, project["id"], "viewer", "owner")

    assert response.status_code == 422


def test_editor_cannot_add_members(client, owner, project):
    editor = create_user(client, "editor")
    create_user(client, "viewer")
    add_member(client, owner, project["id"], "editor", "editor")

    response = add_member(client, editor, project["id"], "viewer", "viewer")

    assert response.status_code == 403


def test_owner_can_remove_member(client, owner, project):
    viewer = create_user(client, "viewer")
    member = add_member(client, owner, project["id"], "viewer", "viewer").json()

    response = client.delete(
        f"{API}/projects/{project['id']}/members/{member['user_id']}",
        headers=auth_header(owner["access_token"]),
    )
    after = client.get(
        f"{API}/projects/{project['id']}", headers=auth_header(viewer["access_token"])
    )

    assert response.status_code == 204
    assert after.status_code == 404


def test_member_can_leave_project(client, owner, project):
    viewer = create_user(client, "viewer")
    member = add_member(client, owner, project["id"], "viewer", "viewer").json()

    response = client.delete(
        f"{API}/projects/{project['id']}/members/{member['user_id']}",
        headers=auth_header(viewer["access_token"]),
    )

    assert response.status_code == 204


def test_member_cannot_remove_other_members(client, owner, project):
    viewer = create_user(client, "viewer")
    create_user(client, "editor")
    add_member(client, owner, project["id"], "viewer", "viewer")
    editor = add_member(client, owner, project["id"], "editor", "editor").json()

    response = client.delete(
        f"{API}/projects/{project['id']}/members/{editor['user_id']}",
        headers=auth_header(viewer["access_token"]),
    )

    assert response.status_code == 403


def test_owner_cannot_be_removed(client, owner, project):
    response = client.delete(
        f"{API}/projects/{project['id']}/members/{project['owner_id']}",
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 400
