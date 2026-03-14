from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_and_list_clubs() -> None:
    create_response = client.post(
        "/api/v1/clubs",
        json={"name": "Demo Club", "description": "Flagship club", "is_active": True},
    )
    assert create_response.status_code == 200
    assert create_response.json()["name"] == "Demo Club"

    list_response = client.get("/api/v1/clubs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "Demo Club"
