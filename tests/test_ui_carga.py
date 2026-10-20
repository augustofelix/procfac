from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.core.esquema import Factura
from tests.pdfs import FACTURA_A

RUTA_UI = str(Path(__file__).resolve().parents[1] / "app" / "ui" / "main.py")


def respuesta(status_code, json=None):
    return httpx.Response(status_code, json=json, request=httpx.Request("POST", "http://test/verificar"))


@pytest.fixture
def at():
    """La UI con una sesión ya iniciada, en la pantalla de carga."""
    at = AppTest.from_file(RUTA_UI)
    at.session_state.token = "t"
    at.session_state.usuario = "ana"
    return at.run()


def subir(at, respuesta_backend):
    at.file_uploader[0].upload("f.pdf", FACTURA_A, "application/pdf")
    with patch("httpx.post", return_value=respuesta_backend) as post:
        at.run()
    return post


def boton(at, etiqueta):
    return next(b for b in at.button if b.label == etiqueta)


def test_selector_admite_un_solo_pdf(at):
    selector = at.file_uploader[0]
    assert selector.allowed_type == [".pdf"]
    assert selector.accept_multiple_files is False


def test_pdf_verificado_muestra_consentimiento_sin_enviarlo_a_claude(at):
    post = subir(at, respuesta(204))
    assert post.call_count == 1
    assert post.call_args.args[0].endswith("/verificar")
    assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer t"}
    assert at.subheader[0].value == "Consentimiento"
    assert "API de Claude" in at.warning[0].value
    assert {b.label for b in at.button} == {"Aceptar y enviar", "Rechazar"}


def test_pdf_rechazado_muestra_motivo_y_vuelve_a_la_carga(at):
    subir(at, respuesta(422, {"detail": {"motivo": "mas_de_una_factura", "mensaje": "El PDF contiene más de una factura."}}))
    assert at.subheader[0].value == "Cargar factura"
    assert at.error[0].value == "El PDF contiene más de una factura."
    assert "pdf" not in at.session_state
    assert at.file_uploader[0].value is None


def test_sesion_perdida_vuelve_al_login(at):
    subir(at, respuesta(401, {"detail": "Sesión no iniciada"}))
    assert at.subheader[0].value == "Iniciar sesión"
    assert at.warning[0].value == "La sesión se perdió. Iniciá sesión de nuevo."
    assert "token" not in at.session_state


def test_backend_caido_muestra_error_y_vuelve_a_la_carga(at):
    at.file_uploader[0].upload("f.pdf", FACTURA_A, "application/pdf")
    with patch("httpx.post", side_effect=httpx.ConnectError("caído")):
        at.run()
    assert at.subheader[0].value == "Cargar factura"
    assert at.error[0].value == "No se pudo conectar con el servidor."


def test_rechazar_consentimiento_vuelve_a_la_carga_sin_llamar_a_claude(at):
    subir(at, respuesta(204))
    with patch("httpx.post") as post:
        boton(at, "Rechazar").click().run()
    post.assert_not_called()
    assert at.subheader[0].value == "Cargar factura"
    assert at.info[0].value == "Proceso cancelado: la factura no se envió."
    assert "pdf" not in at.session_state
    assert at.file_uploader[0].value is None


def test_aceptar_consentimiento_extrae_y_pasa_a_validar(at):
    subir(at, respuesta(204))
    factura = {campo: None for campo in Factura.model_fields}
    with patch("httpx.post", return_value=respuesta(200, factura)) as post:
        boton(at, "Aceptar y enviar").click().run()
    assert post.call_count == 1
    assert post.call_args.args[0].endswith("/extraer")
    assert at.subheader[0].value == "Validar campos"
    assert at.session_state.consentimiento is True
