import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_is_not_plain_text():
    password_hash = hash_password("Secret123")

    assert password_hash != "Secret123"
    assert verify_password("Secret123", password_hash)


def test_wrong_password_is_rejected():
    password_hash = hash_password("Secret123")

    assert not verify_password("Secret124", password_hash)


def test_same_password_gives_different_hashes():
    assert hash_password("Secret123") != hash_password("Secret123")


def test_too_long_password_is_rejected_without_error():
    password_hash = hash_password("Secret123")

    assert not verify_password("a" * 100, password_hash)


def test_access_token_contains_user_id():
    user_id = uuid.uuid4()

    payload = decode_token(create_access_token(user_id), "access")

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token_cannot_be_used_as_access():
    token, _ = create_refresh_token(uuid.uuid4())

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "access")


def test_expired_token_is_rejected():
    token = create_access_token(uuid.uuid4(), expires_delta=timedelta(seconds=-1))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, "access")


def test_tampered_token_is_rejected():
    token = create_access_token(uuid.uuid4())
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}AA"

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered, "access")


def test_token_signed_with_other_key_is_rejected():
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": 9999999999, "iat": 0, "jti": "x"},
        "another-secret-key-another-secret-key",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "access")


def test_unsigned_token_is_rejected():
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": 9999999999, "iat": 0, "jti": "x"},
        key=None,
        algorithm="none",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "access")


def test_token_hash_is_stable():
    assert hash_token("abc") == hash_token("abc")
    assert len(hash_token("abc")) == 64
