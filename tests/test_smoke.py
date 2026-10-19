from fastapi.testclient import TestClient

from app.api.main import app


def test_api_levanta():
    respuesta = TestClient(app).get("/openapi.json")
    assert respuesta.status_code == 200
