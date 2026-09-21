from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_chat_endpoint_returns_json_for_empty_message():
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 200
    assert set(response.json()) == {"answer", "source", "page", "category"}
