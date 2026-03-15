"""Unit tests for security module: password hashing, JWT."""

import pytest

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hash_and_verify():
    """Hashing and verification round-trip."""
    password = "my_secret_password"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_password_hash_different_each_time():
    """Same password produces different hashes (due to salt)."""
    h1 = get_password_hash("same")
    h2 = get_password_hash("same")
    assert h1 != h2
    assert verify_password("same", h1)
    assert verify_password("same", h2)


def test_create_and_decode_access_token():
    """Access token can be created and decoded; contains sub and type."""
    token = create_access_token(123)
    assert isinstance(token, str)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_and_decode_refresh_token():
    """Refresh token has type refresh."""
    token = create_refresh_token(456)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "456"
    assert payload["type"] == "refresh"


def test_decode_invalid_token_returns_none():
    """Invalid or tampered token returns None."""
    assert decode_token("invalid") is None
    assert decode_token("") is None
    token = create_access_token(1)
    assert decode_token(token + "x") is None
