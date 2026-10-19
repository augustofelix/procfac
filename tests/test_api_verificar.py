import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api import auth
from app.api.main import app
from app.core.sesiones import Sesiones
from tests.pdfs import FACTURA_A, factura, generar_pdf


@pytest.fixture
def cliente():
    sesiones = Sesiones()
    app.dependency_overrides[auth.obtener_usuarios] = lambda: {"ana": "clave"}
    app.dependency_overrides[auth.obtener_sesiones] = lambda: sesiones
    cliente = TestClient(app)
    token = cliente.post("/login", json={"usuario": "ana", "contrasena": "clave"}).json()["token"]
    cliente.headers["Authorization"] = f"Bearer {token}"
    yield cliente
    app.dependency_overrides.clear()


def subir(cliente, *archivos, **kwargs):
    return cliente.post("/verificar", files=[("archivo", archivo) for archivo in archivos], **kwargs)


def test_factura_a_responde_204(cliente):
    assert subir(cliente, ("f.pdf", FACTURA_A)).status_code == 204


def test_sin_sesion_responde_401_sin_procesar(cliente, monkeypatch):
    llamadas = []
    monkeypatch.setattr("app.api.verificar.verificar_pdf", lambda *a: llamadas.append(a))
    del cliente.headers["Authorization"]
    assert subir(cliente, ("f.pdf", FACTURA_A)).status_code == 401
    assert llamadas == []


@pytest.mark.parametrize("cantidad", [0, 2, 3])
def test_cantidad_de_archivos_distinta_de_1_responde_422(cliente, cantidad):
    if cantidad == 0:
        respuesta = cliente.post("/verificar", data={"campo": "x"})
    else:
        respuesta = subir(cliente, *[("f.pdf", FACTURA_A)] * cantidad)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["motivo"] == "cantidad_archivos"


def test_sin_cuerpo_responde_422(cliente):
    assert cliente.post("/verificar").status_code == 422


def test_archivo_que_no_es_pdf_responde_422(cliente):
    respuesta = subir(cliente, ("factura.pdf", b"no soy un PDF"))
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["motivo"] == "no_es_pdf"


@pytest.mark.parametrize(
    ("pdf", "motivo", "mensaje"),
    [
        (generar_pdf(*[factura()] * 4), "demasiadas_paginas", "El PDF supera las 3 páginas."),
        (
            generar_pdf(factura(), factura(numeracion="N° 0003-00009999")),
            "mas_de_una_factura",
            "El PDF contiene más de una factura.",
        ),
        (
            generar_pdf(factura(letra="B", codigo="06")),
            "no_factura_a",
            "No se pudo identificar el comprobante como factura A.",
        ),
    ],
)
def test_rechazo_responde_422_con_motivo_y_mensaje(cliente, pdf, motivo, mensaje):
    respuesta = subir(cliente, ("f.pdf", pdf))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": {"motivo": motivo, "mensaje": mensaje}}


def test_pdf_de_mas_de_1_mb_no_se_escribe_en_disco(cliente, monkeypatch):
    def escribir_en_disco(self):
        raise AssertionError("el archivo subido pasó a disco")

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", escribir_en_disco)
    # Un comentario al final agranda el PDF sin cambiar su contenido
    grande = FACTURA_A + b"\n%" + b"x" * 2_000_000
    assert subir(cliente, ("f.pdf", grande)).status_code == 204
