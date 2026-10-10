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

## Роли и права доступа

Глобальная роль пользователя: `user` или `admin`. Администратор управляет учётными
записями, но не имеет доступа к содержимому чужих проектов.

Роль в проекте: `owner`, `editor` или `viewer`.

| Действие | owner | editor | viewer |
|---|:---:|:---:|:---:|
| Просмотр проекта, задач, категорий, комментариев | + | + | + |
| Создание, изменение, удаление задач и категорий, работа с тегами задач | + | + | – |
| Смена статуса задачи | + | + | только исполнитель |
| Комментирование | + | + | + |
| Удаление чужих комментариев | + | – | – |
| Изменение и удаление проекта, управление участниками | + | – | – |

Пользователь, не состоящий в проекте, получает `404`: существование чужих проектов
и задач не раскрывается.

## Жизненный цикл задачи

```
new → in_progress → review → done
                      ↓
                 in_progress (возврат на доработку)
```

Из `new`, `in_progress` и `review` задачу можно перевести в `cancelled`.
Из `done` и `cancelled` переходов нет.

## Эндпоинты

Все пути начинаются с `/api/v1`.

| Группа | Метод и путь | Доступ |
|---|---|---|
| auth | `POST /auth/register` | все |
| | `POST /auth/login` | все |
| | `POST /auth/refresh` | все |
| | `POST /auth/logout` | авторизованный |
| users | `GET /users/me` | авторизованный |
| | `PATCH /users/me` | авторизованный |
| | `PUT /users/me/password` | авторизованный |
| | `GET /users` | admin |
| | `PATCH /users/{user_id}/role` | admin |
| | `DELETE /users/{user_id}` | admin |
| projects | `GET /projects` | авторизованный |
| | `POST /projects` | авторизованный |
| | `GET /projects/{project_id}` | участник |
| | `PATCH /projects/{project_id}` | owner |
| | `DELETE /projects/{project_id}` | owner |
| | `GET /projects/{project_id}/members` | участник |
| | `POST /projects/{project_id}/members` | owner |
| | `DELETE /projects/{project_id}/members/{user_id}` | owner или сам участник |
| tasks | `GET /tasks` | участник |
| | `POST /tasks` | owner, editor |
| | `GET /tasks/{task_id}` | участник |
| | `PATCH /tasks/{task_id}` | owner, editor |
| | `DELETE /tasks/{task_id}` | owner, editor |
| | `PATCH /tasks/{task_id}/status` | owner, editor, исполнитель |
| | `PATCH /tasks/{task_id}/assignee` | owner, editor |
| categories | `GET /categories?project_id=...` | участник |
| | `POST /categories` | owner, editor |
| | `PATCH /categories/{category_id}` | owner, editor |
| | `DELETE /categories/{category_id}` | owner, editor |
| tags | `GET /tags` | авторизованный |
| | `POST /tags` | авторизованный |
| | `POST /tasks/{task_id}/tags` | owner, editor |
| | `DELETE /tasks/{task_id}/tags/{tag_id}` | owner, editor |
| comments | `GET /tasks/{task_id}/comments` | участник |
| | `POST /tasks/{task_id}/comments` | участник |
| | `DELETE /comments/{comment_id}` | автор или owner |

Список задач `GET /tasks` поддерживает фильтры `project_id`, `status`, `priority`,
`assignee_id`, `tag_id`, поиск `search`, сортировку `sort_by` (`created_at`, `deadline`,
`priority`, `title`) с порядком `order` (`asc`, `desc`) и пагинацию `limit`, `offset`.

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
