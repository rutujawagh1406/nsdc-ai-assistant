from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_chat_endpoint_rejects_empty_message():
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_endpoint_rejects_oversized_message():
    response = client.post("/chat", json={"message": "x" * 501})

    assert response.status_code == 422
