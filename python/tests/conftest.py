import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from api.main import app
from api.auth import get_current_user

FAKE_USER = {"user_id": "user_123", "email": "test@example.com"}
FAKE_ORG_ID = "org_123"


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    with patch("api.sales_service._db") as db:
        db.ensure_org.return_value = FAKE_ORG_ID
        db.get_rows.return_value = []
        db.add_row.return_value = None
        db.upsert_row.return_value = None
        db.update_rows.return_value = []
        yield db


