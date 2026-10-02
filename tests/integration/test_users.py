import uuid

from tests.utils import API, auth_header, login, register


def get_me(client, tokens):
    return client.get(f"{API}/users/me", headers=auth_header(tokens["access_token"]))


def test_me_requires_authentication(client):
    response = client.get(f"{API}/users/me")

    assert response.status_code == 401


def test_me_rejects_malformed_token(client):
    response = client.get(f"{API}/users/me", headers=auth_header("abc.def.ghi"))

    assert response.status_code == 401


def test_me_returns_current_user(client, user_tokens):
    response = get_me(client, user_tokens)

    assert response.status_code == 200
    assert response.json()["username"] == "user"


def test_update_profile(client, user_tokens):
    response = client.patch(
        f"{API}/users/me",
        json={"username": "new_name"},
        headers=auth_header(user_tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["username"] == "new_name"


def test_update_profile_with_taken_username_returns_conflict(client, user_tokens):
    register(client, email="second@example.com", username="second")

    response = client.patch(
        f"{API}/users/me",
        json={"username": "second"},
        headers=auth_header(user_tokens["access_token"]),
    )

    assert response.status_code == 409


def test_user_cannot_change_own_role_via_profile(client, user_tokens):
    response = client.patch(
        f"{API}/users/me",
        json={"role": "admin"},
        headers=auth_header(user_tokens["access_token"]),
    )

    assert response.status_code == 422


def test_change_password_requires_current_password(client, user_tokens):
    response = client.put(
        f"{API}/users/me/password",
        json={"current_password": "Wrong123", "new_password": "NewSecret123"},
        headers=auth_header(user_tokens["access_token"]),
    )

    assert response.status_code == 400


def test_change_password_replaces_old_one(client, user_tokens):
    response = client.put(
        f"{API}/users/me/password",
        json={"current_password": "Secret123", "new_password": "NewSecret123"},
        headers=auth_header(user_tokens["access_token"]),
    )
    old_login = client.post(
        f"{API}/auth/login", json={"email": "user@example.com", "password": "Secret123"}
    )
    old_refresh = client.post(
        f"{API}/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}
    )

    assert response.status_code == 204
    assert old_login.status_code == 401
    assert old_refresh.status_code == 401
    assert login(client, password="NewSecret123")["access_token"]


def test_regular_user_cannot_list_users(client, user_tokens):
    response = client.get(f"{API}/users", headers=auth_header(user_tokens["access_token"]))

    assert response.status_code == 403


def test_admin_can_list_users_with_pagination(client, admin_tokens, user_tokens):
    response = client.get(
        f"{API}/users",
        params={"limit": 1, "offset": 0},
        headers=auth_header(admin_tokens["access_token"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_list_users_rejects_invalid_limit(client, admin_tokens):
    response = client.get(
        f"{API}/users", params={"limit": 0}, headers=auth_header(admin_tokens["access_token"])
    )

    assert response.status_code == 422


def test_admin_can_change_user_role(client, admin_tokens, user_tokens):
    user_id = get_me(client, user_tokens).json()["id"]

    response = client.patch(
        f"{API}/users/{user_id}/role",
        json={"role": "admin"},
        headers=auth_header(admin_tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_admin_cannot_change_own_role(client, admin_tokens):
    admin_id = get_me(client, admin_tokens).json()["id"]

    response = client.patch(
        f"{API}/users/{admin_id}/role",
        json={"role": "user"},
        headers=auth_header(admin_tokens["access_token"]),
    )

    assert response.status_code == 400


def test_regular_user_cannot_change_roles(client, user_tokens):
    user_id = get_me(client, user_tokens).json()["id"]

    response = client.patch(
        f"{API}/users/{user_id}/role",
        json={"role": "admin"},
        headers=auth_header(user_tokens["access_token"]),
    )

    assert response.status_code == 403


def test_change_role_of_unknown_user_returns_not_found(client, admin_tokens):
    response = client.patch(
        f"{API}/users/{uuid.uuid4()}/role",
        json={"role": "admin"},
        headers=auth_header(admin_tokens["access_token"]),
    )

    assert response.status_code == 404


def test_deactivated_user_loses_access(client, admin_tokens, user_tokens):
    user_id = get_me(client, user_tokens).json()["id"]

    response = client.delete(
        f"{API}/users/{user_id}", headers=auth_header(admin_tokens["access_token"])
    )

    assert response.status_code == 204
    assert get_me(client, user_tokens).status_code == 401
    old_login = client.post(
        f"{API}/auth/login", json={"email": "user@example.com", "password": "Secret123"}
    )
    assert old_login.status_code == 401


def test_admin_cannot_deactivate_self(client, admin_tokens):
    admin_id = get_me(client, admin_tokens).json()["id"]

    response = client.delete(
        f"{API}/users/{admin_id}", headers=auth_header(admin_tokens["access_token"])
    )

    assert response.status_code == 400
