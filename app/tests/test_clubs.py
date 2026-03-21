from fastapi.testclient import TestClient

from app.core.constants import UserRole
from app.main import app
from app.tests.conftest import create_user_with_token

client = TestClient(app)


def test_create_and_list_clubs() -> None:
    _, headers = create_user_with_token(role=UserRole.PLATFORM_ADMIN.value, email="club-admin@example.com")

    create_response = client.post(
        "/api/v1/clubs",
        json={"name": "Demo Club", "description": "Flagship club", "is_active": True},
        headers=headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["name"] == "Demo Club"

    list_response = client.get("/api/v1/clubs", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "Demo Club"
