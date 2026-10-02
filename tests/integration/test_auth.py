from tests.utils import API, auth_header, login, register


def test_register_returns_user_without_password(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_returns_conflict(client):
    register(client)

    response = register(client, email="USER@example.com", username="other")

    assert response.status_code == 409


def test_register_duplicate_username_returns_conflict(client):
    register(client)

    response = register(client, email="other@example.com")

    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    response = register(client, password="password")

    assert response.status_code == 422


def test_register_rejects_role_field(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": "hacker@example.com",
            "username": "hacker",
            "password": "Secret123",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_login_returns_token_pair(client):
    register(client)

    tokens = login(client)

    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_login_errors_do_not_reveal_existing_email(client):
    register(client)

    wrong_password = client.post(
        f"{API}/auth/login", json={"email": "user@example.com", "password": "Wrong123"}
    )
    unknown_email = client.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": "Wrong123"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_rotates_tokens(client, user_tokens):
    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != user_tokens["refresh_token"]


def test_reused_refresh_token_revokes_all_sessions(client, user_tokens):
    first = client.post(f"{API}/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]})
    new_refresh = first.json()["refresh_token"]

    reuse = client.post(f"{API}/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]})
    after_reuse = client.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})

    assert reuse.status_code == 401
    assert after_reuse.status_code == 401


def test_access_token_cannot_be_used_for_refresh(client, user_tokens):
    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": user_tokens["access_token"]}
    )

    assert response.status_code == 401


def test_invalid_refresh_token_is_rejected(client):
    response = client.post(f"{API}/auth/refresh", json={"refresh_token": "not-a-token"})

    assert response.status_code == 401


def test_logout_requires_authentication(client, user_tokens):
    response = client.post(
        f"{API}/auth/logout", json={"refresh_token": user_tokens["refresh_token"]}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_logout_revokes_refresh_token(client, user_tokens):
    logout = client.post(
        f"{API}/auth/logout",
        json={"refresh_token": user_tokens["refresh_token"]},
        headers=auth_header(user_tokens["access_token"]),
    )
    refresh = client.post(
        f"{API}/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}
    )

    assert logout.status_code == 204
    assert refresh.status_code == 401


def test_logout_cannot_revoke_other_users_token(client, user_tokens):
    register(client, email="second@example.com", username="second")
    second_tokens = login(client, email="second@example.com")

    client.post(
        f"{API}/auth/logout",
        json={"refresh_token": second_tokens["refresh_token"]},
        headers=auth_header(user_tokens["access_token"]),
    )
    refresh = client.post(
        f"{API}/auth/refresh", json={"refresh_token": second_tokens["refresh_token"]}
    )

    assert refresh.status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(client, user_tokens):
    response = client.post(
        f"{API}/auth/logout",
        json={"refresh_token": user_tokens["refresh_token"]},
        headers=auth_header(user_tokens["refresh_token"]),
    )

    assert response.status_code == 401
