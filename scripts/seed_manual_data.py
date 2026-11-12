import argparse
import http.client
import json
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

USERS = ["alice", "bob", "carol", "dave", "eve"]


class Api:
    def __init__(self, base_url: str) -> None:
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise SystemExit("Адрес API должен начинаться с http:// или https://")
        connection_class = (
            http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        )
        self.connection = connection_class(parts.hostname, parts.port, timeout=10)

    def request(
        self, method: str, path: str, body: dict | None = None, token: str | None = None
    ) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = json.dumps(body) if body is not None else None
        try:
            self.connection.request(method, f"/api/v1{path}", body=payload, headers=headers)
            response = self.connection.getresponse()
        except OSError as exc:
            raise SystemExit(
                f"Не удалось подключиться к API: {exc}. Приложение запущено?"
            ) from None
        raw = response.read()
        return response.status, json.loads(raw) if raw else {}

    def expect(self, expected: int, method: str, path: str, **kwargs) -> dict:
        status, data = self.request(method, path, **kwargs)
        if status != expected:
            raise SystemExit(f"{method} {path}: ожидался код {expected}, получен {status}: {data}")
        return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Создание базового состояния для ручного тестирования"
    )
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--password", default="Secret123", help="Пароль тестовых пользователей")
    args = parser.parse_args(argv)
    api = Api(args.url)

    tokens: dict[str, str] = {}
    user_ids: dict[str, str] = {}
    for name in USERS:
        email = f"{name}@example.com"
        status, _ = api.request(
            "POST",
            "/auth/register",
            body={"email": email, "username": name, "password": args.password},
        )
        if status not in {201, 409}:
            raise SystemExit(f"Не удалось зарегистрировать {name}: код {status}")
        login = api.expect(
            200, "POST", "/auth/login", body={"email": email, "password": args.password}
        )
        tokens[name] = login["access_token"]
        user_ids[name] = api.expect(200, "GET", "/users/me", token=tokens[name])["id"]

    project = api.expect(
        201, "POST", "/projects", body={"title": "Проект P"}, token=tokens["alice"]
    )
    for name, role in [("bob", "editor"), ("carol", "viewer")]:
        api.expect(
            201,
            "POST",
            f"/projects/{project['id']}/members",
            body={"username": name, "role": role},
            token=tokens["alice"],
        )
    deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    task = api.expect(
        201,
        "POST",
        "/tasks",
        body={
            "project_id": project["id"],
            "title": "Задача T",
            "priority": "high",
            "deadline": deadline,
        },
        token=tokens["alice"],
    )

    print("Базовое состояние создано. Пароль всех пользователей:", args.password)
    for name in USERS:
        print(f"  {name:<6} {name}@example.com  id = {user_ids[name]}")
    print(f"  Проект P  id = {project['id']}")
    print(f"  Задача T  id = {task['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
