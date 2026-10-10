import uuid

import pytest

from app.services.category_service import MAX_CATEGORIES_PER_PROJECT
from tests.utils import API, add_member, auth_header, create_project, create_user


@pytest.fixture
def owner(client):
    return create_user(client, "owner")


@pytest.fixture
def project(client, owner):
    return create_project(client, owner)


def create_category(client, tokens, project_id, name="Работа"):
    return client.post(
        f"{API}/categories",
        json={"project_id": project_id, "name": name},
        headers=auth_header(tokens["access_token"]),
    )


def list_categories(client, tokens, project_id):
    return client.get(
        f"{API}/categories",
        params={"project_id": project_id},
        headers=auth_header(tokens["access_token"]),
    )


def test_create_category(client, owner, project):
    response = create_category(client, owner, project["id"], name="  Учёба  ")

    assert response.status_code == 201
    assert response.json()["name"] == "Учёба"


def test_list_categories_sorted_by_name(client, owner, project):
    for name in ["Работа", "Дом", "Учёба"]:
        create_category(client, owner, project["id"], name=name)

    response = list_categories(client, owner, project["id"])

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Дом", "Работа", "Учёба"]


def test_list_requires_project_id(client, owner):
    response = client.get(f"{API}/categories", headers=auth_header(owner["access_token"]))

    assert response.status_code == 422


def test_duplicate_name_is_rejected_case_insensitive(client, owner, project):
    create_category(client, owner, project["id"], name="Работа")

    response = create_category(client, owner, project["id"], name="РАБОТА")

    assert response.status_code == 409


def test_same_name_allowed_in_different_projects(client, owner, project):
    other = create_project(client, owner, title="Другой")
    create_category(client, owner, project["id"], name="Работа")

    response = create_category(client, owner, other["id"], name="Работа")

    assert response.status_code == 201


@pytest.mark.parametrize("name", ["   ", "a" * 101, "bad\u0000name"])
def test_invalid_name_is_rejected(client, owner, project, name):
    response = create_category(client, owner, project["id"], name=name)

    assert response.status_code == 422


def test_category_limit_per_project(client, owner, project):
    for number in range(MAX_CATEGORIES_PER_PROJECT):
        create_category(client, owner, project["id"], name=f"Категория {number}")

    response = create_category(client, owner, project["id"], name="Лишняя")

    assert response.status_code == 400


def test_viewer_can_list_but_cannot_create(client, owner, project):
    viewer = create_user(client, "viewer")
    add_member(client, owner, project["id"], "viewer", "viewer")

    listed = list_categories(client, viewer, project["id"])
    created = create_category(client, viewer, project["id"])

    assert listed.status_code == 200
    assert created.status_code == 403


def test_stranger_cannot_see_categories(client, owner, project):
    category = create_category(client, owner, project["id"]).json()
    stranger = create_user(client, "stranger")

    listed = list_categories(client, stranger, project["id"])
    renamed = client.patch(
        f"{API}/categories/{category['id']}",
        json={"name": "Взлом"},
        headers=auth_header(stranger["access_token"]),
    )

    assert listed.status_code == 404
    assert renamed.status_code == 404


def test_editor_can_rename_category(client, owner, project):
    editor = create_user(client, "editor")
    add_member(client, owner, project["id"], "editor", "editor")
    category = create_category(client, owner, project["id"]).json()

    response = client.patch(
        f"{API}/categories/{category['id']}",
        json={"name": "Срочное"},
        headers=auth_header(editor["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Срочное"


def test_rename_to_existing_name_is_rejected(client, owner, project):
    create_category(client, owner, project["id"], name="Дом")
    category = create_category(client, owner, project["id"], name="Работа").json()

    response = client.patch(
        f"{API}/categories/{category['id']}",
        json={"name": "дом"},
        headers=auth_header(owner["access_token"]),
    )

    assert response.status_code == 409


def test_unknown_category_returns_not_found(client, owner):
    response = client.delete(
        f"{API}/categories/{uuid.uuid4()}", headers=auth_header(owner["access_token"])
    )

    assert response.status_code == 404


def test_deleting_category_clears_it_from_tasks(client, owner, project):
    category = create_category(client, owner, project["id"]).json()
    task = client.post(
        f"{API}/tasks",
        json={"project_id": project["id"], "title": "Задача", "category_id": category["id"]},
        headers=auth_header(owner["access_token"]),
    ).json()

    deleted = client.delete(
        f"{API}/categories/{category['id']}", headers=auth_header(owner["access_token"])
    )
    after = client.get(f"{API}/tasks/{task['id']}", headers=auth_header(owner["access_token"]))

    assert task["category_id"] == category["id"]
    assert deleted.status_code == 204
    assert after.json()["category_id"] is None
