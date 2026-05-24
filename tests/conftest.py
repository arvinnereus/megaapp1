import pytest
import os
import sys
import socket
import threading
import time

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db as _db


# ── Unit test fixtures ─────────────────────────────────────────────────

@pytest.fixture
def app():
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["ADMIN_USER"] = "admin"
    os.environ["ADMIN_PASS"] = "admin"
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"}, follow_redirects=True)
    return client


# ── Playwright E2E fixtures ───────────────────────────────────────────

def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    """Start Flask on a real port in a daemon thread for Playwright tests."""
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["SECRET_KEY"] = "test-secret-e2e"
    os.environ["ADMIN_USER"] = "admin"
    os.environ["ADMIN_PASS"] = "testpass123"

    app = create_app()
    app.config["TESTING"] = True

    port = _find_free_port()
    thread = threading.Thread(
        target=app.run,
        daemon=True,
        kwargs={"host": "127.0.0.1", "port": port, "use_reloader": False},
    )
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Flask live server did not start")

    yield f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def base_url(live_server):
    """Override pytest-playwright's built-in base_url fixture."""
    return live_server
