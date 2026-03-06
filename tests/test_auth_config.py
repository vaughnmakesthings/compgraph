"""Tests for Supabase Auth configuration settings (SEC-01)."""

import pytest
from pydantic import ValidationError

from compgraph.config import Settings


def test_auth_disabled_blocked_in_production():
    """AUTH_DISABLED=true must raise when ENVIRONMENT=production."""
    with pytest.raises(ValidationError, match=r"AUTH_DISABLED.*only allowed when ENVIRONMENT=test"):
        Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="production")


def test_auth_disabled_blocked_in_dev():
    """AUTH_DISABLED=true must raise when ENVIRONMENT=dev (internet-facing)."""
    with pytest.raises(ValidationError, match=r"AUTH_DISABLED.*only allowed when ENVIRONMENT=test"):
        Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="dev")


def test_auth_disabled_allowed_in_test():
    """AUTH_DISABLED=true is only allowed in test environment."""
    s = Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="test")
    assert s.AUTH_DISABLED is True


def test_auth_fields_default_empty():
    """New auth fields default to safe values when auth is disabled."""
    s = Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="test")
    assert s.SUPABASE_JWT_SECRET.get_secret_value() == ""
    assert s.SUPABASE_SERVICE_ROLE_KEY.get_secret_value() == ""
    assert s.AUTH_DISABLED is True


def test_jwt_secret_too_short_rejected():
    """Short JWT secret must raise when auth is enabled."""
    with pytest.raises(ValidationError, match=r"SUPABASE_JWT_SECRET must be at least 32 bytes"):
        Settings(DATABASE_PASSWORD="x", SUPABASE_JWT_SECRET="short", AUTH_DISABLED=False)


def test_jwt_secret_empty_rejected():
    """Empty JWT secret must raise when auth is enabled."""
    with pytest.raises(ValidationError, match=r"SUPABASE_JWT_SECRET must be at least 32 bytes"):
        Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=False)


def test_jwt_secret_valid_when_long_enough():
    """32+ byte JWT secret passes validation."""
    s = Settings(
        DATABASE_PASSWORD="x",
        SUPABASE_JWT_SECRET="a" * 32,
        AUTH_DISABLED=False,
    )
    assert len(s.SUPABASE_JWT_SECRET.get_secret_value()) == 32


def test_jwt_secret_not_checked_when_auth_disabled():
    """Short/empty JWT secret is fine when AUTH_DISABLED=True."""
    s = Settings(
        DATABASE_PASSWORD="x", SUPABASE_JWT_SECRET="short", AUTH_DISABLED=True, ENVIRONMENT="test"
    )
    assert s.SUPABASE_JWT_SECRET.get_secret_value() == "short"
