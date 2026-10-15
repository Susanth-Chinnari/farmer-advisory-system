"""
conftest.py - Pytest Test Configuration and Fixtures

Beginner-Friendly Explanation:
In automated testing, "fixtures" are setup routines that run before each test.
This fixture sets up an isolated test environment with a temporary SQLite database
so that running tests does not modify your real development data.
"""

import os
import tempfile
import pytest
from run import create_app
from backend.database import init_db
import backend.config as config


@pytest.fixture
def app():
    """Creates a temporary Flask app instance configured for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    upload_tmp = tempfile.mkdtemp()

    # Override config paths for testing
    original_db = config.DATABASE_PATH
    original_upload = config.UPLOAD_FOLDER
    config.DATABASE_PATH = db_path
    config.UPLOAD_FOLDER = upload_tmp

    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-for-pytest',
        'WTF_CSRF_ENABLED': False
    })

    with app.app_context():
        init_db()

    yield app

    # Cleanup temporary resources after test finishes
    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)
    config.DATABASE_PATH = original_db
    config.UPLOAD_FOLDER = original_upload


@pytest.fixture
def client(app):
    """Provides a test HTTP client to send simulated web requests."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Provides a test client with a pre-authenticated farmer session."""
    client.post('/api/auth/register', json={
        'username': 'test_farmer',
        'password': 'Password@123',
        'full_name': 'Test Farmer',
        'location': 'Karnal, Haryana'
    })
    return client
