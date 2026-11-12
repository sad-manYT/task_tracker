import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.comment import CommentCreate
from app.schemas.project import MemberAdd, ProjectCreate, ProjectUpdate
from app.schemas.tag import TagCreate
from app.schemas.task import TaskCreate, TaskQuery, TaskUpdate

PROJECT_ID = str(uuid.uuid4())


def register(**overrides):
    data = {"email": "user@example.com", "username": "user", "password": "Secret123"}
    return RegisterRequest(**(data | overrides))


def test_email_is_lowercased():
    assert register(email="User@Example.COM").email == "user@example.com"


@pytest.mark.parametrize("password", ["short1", "onlyletters", "12345678", "Ж" * 36 + "1"])
def test_weak_or_too_long_password_is_rejected(password):
    with pytest.raises(ValidationError):
        register(password=password)


def test_password_with_cyrillic_letters_is_accepted():
    assert register(password="Пароль123").password == "Пароль123"


@pytest.mark.parametrize("username", ["ab", "a" * 51, "user name", "юзер", "user!"])
def test_invalid_username_is_rejected(username):
    with pytest.raises(ValidationError):
        register(username=username)


def test_unknown_fields_are_forbidden():
    with pytest.raises(ValidationError):
        register(role="admin")


def test_title_is_stripped():
    assert ProjectCreate(title="  Проект  ").title == "Проект"


@pytest.mark.parametrize("title", ["", "   ", "a" * 201, "a\x00b"])
def test_invalid_title_is_rejected(title):
    with pytest.raises(ValidationError):
        ProjectCreate(title=title)


def test_project_update_keeps_only_sent_fields():
    data = ProjectUpdate(description=None)

    assert data.model_dump(exclude_unset=True) == {"description": None}


def test_project_title_cannot_be_null_on_update():
    with pytest.raises(ValidationError):
        ProjectUpdate(title=None)


def test_member_cannot_be_added_as_owner():
    with pytest.raises(ValidationError):
        MemberAdd(username="user", role="owner")


def test_member_role_defaults_to_viewer():
    assert MemberAdd(username="user").role == "viewer"


def test_future_deadline_is_accepted():
    deadline = datetime.now(UTC) + timedelta(days=1)

    assert TaskCreate(project_id=PROJECT_ID, title="Задача", deadline=deadline).deadline


@pytest.mark.parametrize(
    "deadline",
    [
        "2020-01-01T00:00:00Z",
        "2030-01-01T00:00:00",
        "2101-01-01T00:00:00Z",
        "9999-12-31T23:59:59-10:00",
    ],
)
def test_invalid_deadline_is_rejected(deadline):
    with pytest.raises(ValidationError):
        TaskCreate(project_id=PROJECT_ID, title="Задача", deadline=deadline)


@pytest.mark.parametrize("field", ["title", "priority"])
def test_required_task_fields_cannot_be_null_on_update(field):
    with pytest.raises(ValidationError):
        TaskUpdate(**{field: None})


def test_task_deadline_can_be_cleared():
    assert TaskUpdate(deadline=None).model_dump(exclude_unset=True) == {"deadline": None}


def test_task_query_defaults():
    query = TaskQuery()

    assert (query.sort_by, query.order, query.limit, query.offset) == (
        "created_at",
        "desc",
        20,
        0,
    )


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"sort_by": "password_hash"},
        {"search": "   "},
        {"unknown": "1"},
    ],
)
def test_invalid_task_query_is_rejected(params):
    with pytest.raises(ValidationError):
        TaskQuery(**params)


def test_tag_name_is_normalized():
    assert TagCreate(name="  Срочно ").name == "срочно"


@pytest.mark.parametrize("name", ["", "a" * 51, "<script>", "a;b", "a\x00"])
def test_invalid_tag_name_is_rejected(name):
    with pytest.raises(ValidationError):
        TagCreate(name=name)


def test_comment_is_stripped():
    assert CommentCreate(body="  Текст  ").body == "Текст"


@pytest.mark.parametrize("body", ["", "   ", "a" * 2001, "a\x00b"])
def test_invalid_comment_is_rejected(body):
    with pytest.raises(ValidationError):
        CommentCreate(body=body)
