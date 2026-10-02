import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.models.enums import UserRole
from app.schemas.auth import RegisterRequest


def create_admin(email: str, username: str) -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing is not None:
            existing.role = UserRole.ADMIN
            db.commit()
            print(f"Пользователь {existing.email} назначен администратором")
            return 0

        password = getpass.getpass("Пароль администратора: ")
        try:
            data = RegisterRequest(email=email, username=username, password=password)
        except ValidationError as exc:
            for error in exc.errors():
                print(f"Ошибка в поле {error['loc'][0]}: {error['msg']}")
            return 1

        db.add(
            User(
                email=data.email,
                username=data.username,
                password_hash=hash_password(data.password),
                role=UserRole.ADMIN,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            print("Имя пользователя уже занято")
            return 1
        print(f"Администратор {data.email} создан")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    admin_parser = commands.add_parser("create-admin", help="Создать администратора")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--username", required=True)

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        return create_admin(args.email, args.username)
    return 1


if __name__ == "__main__":
    sys.exit(main())
