"""Tests for Supabase Auth configuration settings (SEC-01)."""

import pytest
from pydantic import ValidationError

from compgraph.config import Settings


def test_auth_disabled_blocked_in_production():
    """AUTH_DISABLED=true must raise when ENVIRONMENT=production."""
    with pytest.raises(ValidationError, match=r"AUTH_DISABLED.*forbidden"):
        Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="production")


def test_auth_disabled_allowed_in_dev():
    """AUTH_DISABLED=true is fine in dev/test."""
    s = Settings(DATABASE_PASSWORD="x", AUTH_DISABLED=True, ENVIRONMENT="dev")
    assert s.AUTH_DISABLED is True


def test_auth_fields_default_empty():
    """New auth fields default to safe values so existing tests aren't broken."""
    s = Settings(DATABASE_PASSWORD="x")
    assert s.SUPABASE_JWT_SECRET == ""
    assert s.SUPABASE_SERVICE_ROLE_KEY.get_secret_value() == ""
    assert s.AUTH_DISABLED is False
