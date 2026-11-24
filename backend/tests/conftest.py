import os
import tempfile
from pathlib import Path

# must be set BEFORE the app is imported
_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp.as_posix()}",
    ANTHROPIC_API_KEY="",
    LLM_MODE="demo",
    INLINE_JOBS="true",
    SEED_DEMO="true",
    JWT_SECRET="test-secret",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def tokens(client):
    out = {}
    for role, email in [("admin", "admin"), ("support", "support"), ("quality", "quality"), ("operations", "ops"),
                        ("finance", "finance"), ("sales", "sales"), ("executive", "exec")]:
        r = client.post("/api/auth/login", json={"email": f"{email}@demo.local", "password": "demo1234"})
        assert r.status_code == 200, r.text
        out[role] = {"Authorization": f"Bearer {r.json()['token']}"}
    return out
