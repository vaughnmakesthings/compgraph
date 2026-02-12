import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client that bypasses DB connection for unit tests."""
    import os

    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    from compgraph.main import app

    with TestClient(app) as c:
        yield c
