import os
import pytest
from app import create_app
from app.database import get_db, init_db

@pytest.fixture
def app():
    # Use temporary test database
    test_db_path = os.path.join(os.path.dirname(__file__), "test_rpi_control.db")
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-12345",
        "database": {"path": test_db_path}
    })

    with app.app_context():
        init_db()

    yield app

    # Cleanup test db
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    # Log in as default admin
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["_csrf_token"] = "test-csrf-token"
    return client
