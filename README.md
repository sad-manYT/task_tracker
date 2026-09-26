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
