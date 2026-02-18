from __future__ import annotations

import ast
from pathlib import Path

ALEMBIC_ENV_PATH = Path(__file__).resolve().parent.parent / "alembic" / "env.py"


def _parse_get_url_source() -> ast.FunctionDef:
    tree = ast.parse(ALEMBIC_ENV_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_url":
            return node
    raise AssertionError("get_url() function not found in alembic/env.py")


def test_get_url_returns_database_url_direct():
    source = ALEMBIC_ENV_PATH.read_text()
    assert "database_url_direct" in source
    assert "settings.database_url_direct" in source


def test_get_url_does_not_use_pooler_url():
    source = ALEMBIC_ENV_PATH.read_text()
    fn = _parse_get_url_source()
    fn_source = ast.get_source_segment(source, fn)
    assert fn_source is not None
    assert "settings.database_url\n" not in fn_source
    assert "return settings.database_url\n" not in fn_source


def test_get_url_supports_env_override():
    source = ALEMBIC_ENV_PATH.read_text()
    fn = _parse_get_url_source()
    fn_source = ast.get_source_segment(source, fn)
    assert fn_source is not None
    assert "ALEMBIC_DATABASE_URL" in fn_source


def test_get_url_env_override_takes_precedence():
    fn = _parse_get_url_source()
    body = fn.body
    try_block = next(n for n in body if isinstance(n, ast.Try))
    try_body = try_block.body
    env_check_found = False
    return_direct_found = False
    for stmt in try_body:
        if isinstance(stmt, ast.If):
            if_source = ast.dump(stmt.test)
            if "env_override" in if_source or "ALEMBIC_DATABASE_URL" in ast.dump(stmt):
                env_check_found = True
        if isinstance(stmt, ast.Return):
            ret_source = ast.dump(stmt.value)
            if "database_url_direct" in ret_source:
                return_direct_found = True
    assert env_check_found, "ALEMBIC_DATABASE_URL env var check not found in try block"
    assert return_direct_found, "settings.database_url_direct return not found in try block"


def test_database_url_direct_uses_direct_host():
    from compgraph.config import settings

    url = settings.database_url_direct
    assert "db." in url
    assert ".supabase.co" in url
    assert "pooler.supabase.com" not in url


def test_database_url_uses_pooler_host():
    from compgraph.config import settings

    url = settings.database_url
    assert "pooler.supabase.com" in url
    assert "db." not in url


def test_get_url_fallback_to_database_url_env():
    source = ALEMBIC_ENV_PATH.read_text()
    fn = _parse_get_url_source()
    fn_source = ast.get_source_segment(source, fn)
    assert fn_source is not None
    assert "DATABASE_URL" in fn_source
