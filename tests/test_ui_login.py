from pathlib import Path
from unittest.mock import patch

import httpx
from streamlit.testing.v1 import AppTest

RUTA_UI = str(Path(__file__).resolve().parents[1] / "app" / "ui" / "main.py")


def respuesta(status_code, json=None):
    return httpx.Response(status_code, json=json, request=httpx.Request("POST", "http://test/login"))


def ingresar(contrasena, respuesta_backend):
    at = AppTest.from_file(RUTA_UI).run()
    at.text_input[0].input("ana")
    at.text_input[1].input(contrasena)
    with patch("httpx.post", return_value=respuesta_backend):
        at.button[0].click().run()
    return at


def test_login_correcto_muestra_pantalla_de_carga():
    at = ingresar("clave", respuesta(200, {"token": "t"}))
    assert at.session_state.token == "t"
    assert at.subheader[0].value == "Cargar factura"


def test_login_incorrecto_no_muestra_pantalla_de_carga():
    at = ingresar("mal", respuesta(401, {"detail": "x"}))
    assert "token" not in at.session_state
    assert at.subheader[0].value == "Iniciar sesión"
    assert at.error[0].value == "Usuario o contraseña incorrectos."


def test_backend_caido_muestra_error():
    at = AppTest.from_file(RUTA_UI).run()
    with patch("httpx.post", side_effect=httpx.ConnectError("caído")):
        at.button[0].click().run()
    assert "token" not in at.session_state
    assert at.error[0].value == "No se pudo conectar con el servidor."
