from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import auth
from app.core.sesiones import Sesiones

USUARIOS = {f"usuario{n}": f"clave{n}" for n in range(1, 6)}


@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(auth.router)

    # Endpoint de prueba que representa a los de procesamiento
    @app.get("/protegido")
    def protegido(usuario: Annotated[str, Depends(auth.usuario_actual)]):
        return {"usuario": usuario}

    sesiones = Sesiones()
    app.dependency_overrides[auth.obtener_usuarios] = lambda: USUARIOS
    app.dependency_overrides[auth.obtener_sesiones] = lambda: sesiones
    return TestClient(app)


def login(cliente, usuario, contrasena):
    return cliente.post("/login", json={"usuario": usuario, "contrasena": contrasena})


def test_login_correcto_devuelve_token(cliente):
    respuesta = login(cliente, "usuario1", "clave1")
    assert respuesta.status_code == 200
    assert respuesta.json()["token"]


@pytest.mark.parametrize(
    ("usuario", "contrasena"),
    [("usuario1", "mal"), ("desconocido", "clave1"), ("", "")],
)
def test_login_incorrecto_responde_401(cliente, usuario, contrasena):
    respuesta = login(cliente, usuario, contrasena)
    assert respuesta.status_code == 401
    assert "token" not in respuesta.json()


def test_sin_sesion_responde_401(cliente):
    respuesta = cliente.get("/protegido")
    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_token_desconocido_responde_401(cliente):
    respuesta = cliente.get("/protegido", headers={"Authorization": "Bearer inventado"})
    assert respuesta.status_code == 401


def test_cada_token_identifica_a_su_usuario(cliente):
    token_a = login(cliente, "usuario1", "clave1").json()["token"]
    token_b = login(cliente, "usuario2", "clave2").json()["token"]
    assert token_a != token_b
    for token, usuario in [(token_a, "usuario1"), (token_b, "usuario2")]:
        respuesta = cliente.get("/protegido", headers={"Authorization": f"Bearer {token}"})
        assert respuesta.json() == {"usuario": usuario}


def test_5_usuarios_inician_sesion_a_la_vez(cliente):
    with ThreadPoolExecutor(max_workers=5) as pool:
        respuestas = list(pool.map(lambda u: login(cliente, u, USUARIOS[u]), USUARIOS))
    assert [r.status_code for r in respuestas] == [200] * 5
    assert len({r.json()["token"] for r in respuestas}) == 5
