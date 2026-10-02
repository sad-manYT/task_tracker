# Task Tracker API

Backend-приложение «Список задач» с REST API.

Стек: Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, JWT.

## Запуск через Docker

```bash
cp .env.example .env        # затем задать свои пароль БД и JWT_SECRET_KEY
docker compose up --build
```

После запуска:

- API: http://localhost:8000
- Документация Swagger: http://localhost:8000/docs
- Проверка работоспособности: http://localhost:8000/health

## Локальная разработка

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

Проверка кода и запуск тестов:

```bash
ruff check .            # линтер
ruff format .           # форматирование
pytest --cov            # тесты с покрытием
```

## Миграции базы данных

```bash
alembic revision --autogenerate -m "описание изменений"
alembic upgrade head
```

## Создание администратора

Роль администратора нельзя получить через API. Администратор создаётся командой:

```bash
# при запуске через Docker
docker compose exec app python -m app.cli create-admin --email admin@example.com --username admin

# при локальном запуске
python -m app.cli create-admin --email admin@example.com --username admin
```

Если пользователь с таким email уже существует, ему будет назначена роль администратора.

## Аутентификация

1. Зарегистрироваться: `POST /api/v1/auth/register`.
2. Войти: `POST /api/v1/auth/login`, в ответе будут `access_token` и `refresh_token`.
3. Передавать access-токен в заголовке `Authorization: Bearer <токен>`.
   В Swagger для этого есть кнопка **Authorize**.
4. Access-токен действует 15 минут. Новую пару токенов можно получить через
   `POST /api/v1/auth/refresh`.

## Структура проекта

```
app/
  api/v1/      — эндпоинты
  core/        — настройки и безопасность
  db/          — подключение к БД
  models/      — ORM-модели
  schemas/     — схемы валидации (Pydantic)
  services/    — бизнес-логика
alembic/       — миграции
tests/
  unit/        — модульные тесты
  integration/ — интеграционные тесты
```
