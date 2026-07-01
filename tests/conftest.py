# ============================================================
# Pytest fixtures — in-memory SQLite app for testing
# ============================================================
import pytest
from app import create_app, db
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def new_user(app):
    from src.models.user import User
    user = User(username="testuser", email="test@example.com",
                 first_name="Test", last_name="User", role="user")
    user.set_password("Password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_client(client, new_user):
    client.post("/auth/login", data={
        "identifier": "test@example.com",
        "password": "Password123",
    }, follow_redirects=True)
    return client
