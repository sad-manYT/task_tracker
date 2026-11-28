import argparse
import getpass
import http.client
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

OPTIONS_TEMPLATE = """replacer.full_list(0).description=jwt-auth
replacer.full_list(0).enabled=true
replacer.full_list(0).matchtype=REQ_HEADER
replacer.full_list(0).matchstr=Authorization
replacer.full_list(0).regex=false
replacer.full_list(0).replacement=Bearer {token}
"""


def request(
    base_url: str, method: str, path: str, body: dict | None = None, token: str | None = None
) -> tuple[int, dict]:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise SystemExit("Адрес API должен начинаться с http:// или https://")
    connection_class = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(body) if body is not None else None
    connection = connection_class(parts.hostname, parts.port, timeout=10)
    try:
        connection.request(method, f"/api/v1{path}", body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
    except OSError as exc:
        raise SystemExit(f"Не удалось подключиться к API: {exc}. Приложение запущено?") from None
    finally:
        connection.close()
    return response.status, json.loads(raw) if raw else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Создание файла настроек ZAP с токеном администратора для сканирования API"
    )
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--output", default="zap-work/options.prop")
    args = parser.parse_args(argv)

    password = getpass.getpass(f"Пароль {args.email}: ")
    status, data = request(
        args.url, "POST", "/auth/login", body={"email": args.email, "password": password}
    )
    if status != 200:
        raise SystemExit(f"Вход не выполнен (код {status}). Проверьте email и пароль.")
    token = data["access_token"]

    status, profile = request(args.url, "GET", "/users/me", token=token)
    if status != 200:
        raise SystemExit(f"Не удалось проверить токен (код {status}).")
    if profile.get("role") != "admin":
        print(
            "Предупреждение: пользователь не администратор, эндпоинты /users останутся закрытыми."
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(OPTIONS_TEMPLATE.format(token=token), encoding="utf-8")
    print(f"Файл {output} создан. Он содержит токен, не добавляйте его в Git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
