import pytest

from tests.utils import API, auth_header

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "cross-origin-resource-policy": "same-origin",
}


def assert_security_headers(response):
    for name, value in EXPECTED_HEADERS.items():
        assert response.headers[name] == value


def test_headers_on_successful_response(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert_security_headers(response)


def test_headers_on_authenticated_response(client, user_tokens):
    response = client.get(f"{API}/users/me", headers=auth_header(user_tokens["access_token"]))

    assert response.status_code == 200
    assert_security_headers(response)


@pytest.mark.parametrize(
    ("method", "path", "status_code"),
    [
        ("GET", f"{API}/users/me", 401),
        ("GET", "/unknown", 404),
        ("DELETE", "/health", 405),
        ("POST", f"{API}/auth/login", 422),
    ],
)
def test_headers_on_error_responses(client, method, path, status_code):
    response = client.request(method, path, json={} if method == "POST" else None)

    assert response.status_code == status_code
    assert_security_headers(response)


def test_swagger_ui_still_available_with_headers(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()
    assert_security_headers(response)


def test_api_responses_are_not_cacheable(client, user_tokens):
    login = client.post(
        f"{API}/auth/login", json={"email": "user@example.com", "password": "Secret123"}
    )
    profile = client.get(f"{API}/users/me", headers=auth_header(user_tokens["access_token"]))
    unauthorized = client.get(f"{API}/users/me")

    for response in (login, profile, unauthorized):
        assert response.headers["cache-control"] == "no-store"


def test_non_api_responses_keep_default_caching(client):
    response = client.get("/health")

    assert "cache-control" not in response.headers
