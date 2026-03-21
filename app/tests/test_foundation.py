import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parents[2]


def test_root_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_database_url_fails_in_clean_env(tmp_path: Path) -> None:
    env = {
        "PYTHONPATH": str(ROOT_DIR),
        "JWT_SECRET_KEY": "test-secret",
    }
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import Settings; Settings()"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "database_url" in (result.stderr + result.stdout).lower()


def test_missing_jwt_secret_key_fails_in_clean_env(tmp_path: Path) -> None:
    env = {
        "PYTHONPATH": str(ROOT_DIR),
        "DATABASE_URL": "sqlite:///./test.db",
    }
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import Settings; Settings()"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "jwt_secret_key" in (result.stderr + result.stdout).lower()
