from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_reservation() -> None:
    response = client.post(
        "/api/v1/reservations",
        json={"seat_id": 1, "user_id": 1, "status": "pending"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 2
