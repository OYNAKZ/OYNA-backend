from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_clubs() -> None:
    response = client.get("/api/v1/clubs")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Demo Club"
