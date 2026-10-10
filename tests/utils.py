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


def create_user(client: TestClient, name: str) -> dict[str, str]:
    email = f"{name}@example.com"
    response = register(client, email=email, username=name)
    assert response.status_code == 201, response.text
    return login(client, email=email)


def create_project(client: TestClient, tokens: dict[str, str], title: str = "Проект") -> dict:
    response = client.post(
        f"{API}/projects", json={"title": title}, headers=auth_header(tokens["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_member(
    client: TestClient, owner_tokens: dict[str, str], project_id: str, username: str, role: str
):
    return client.post(
        f"{API}/projects/{project_id}/members",
        json={"username": username, "role": role},
        headers=auth_header(owner_tokens["access_token"]),
    )
