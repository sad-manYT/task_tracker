from fastapi.testclient import TestClient

API = "/api/v1"
DEFAULT_EMAIL = "user@example.com"
DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD = "Secret123"


def register(
    client: TestClient,
    email: str = DEFAULT_EMAIL,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
):
    return client.post(
        f"{API}/auth/register",
        json={"email": email, "username": username, "password": password},
    )


def login(
    client: TestClient, email: str = DEFAULT_EMAIL, password: str = DEFAULT_PASSWORD
) -> dict[str, str]:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
