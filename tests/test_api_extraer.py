import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api import auth, extraer
from app.api.main import app
from app.core.esquema import Factura, Item
from app.core.extraccion import Extractor
from app.core.sesiones import Sesiones
from tests.claude_simulado import ClaudeSimulado, factura, respuesta
from tests.pdfs import FACTURA_A, factura as encabezado, generar_pdf

USUARIOS = {"ana": "clave-ana", "beto": "clave-beto"}


@pytest.fixture
def claude():
    return ClaudeSimulado()


@pytest.fixture
def cliente(claude):
    sesiones = Sesiones()
    app.dependency_overrides[auth.obtener_usuarios] = lambda: USUARIOS
    app.dependency_overrides[auth.obtener_sesiones] = lambda: sesiones
    app.dependency_overrides[extraer.obtener_extractor] = lambda: Extractor(claude, "claude-opus-5-5", "low", 5)
    yield TestClient(app)
    app.dependency_overrides.clear()


def autorizacion(cliente, usuario):
    token = cliente.post("/login", json={"usuario": usuario, "contrasena": USUARIOS[usuario]}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def subir(cliente, pdf, usuario="ana"):
    return cliente.post("/extraer", files={"archivo": ("f.pdf", pdf)}, headers=autorizacion(cliente, usuario))


def test_devuelve_los_campos_en_la_misma_respuesta(cliente, claude):
    claude.resultado = respuesta(
        factura(
            punto_venta=3,
            total=121.0,
            impuestos=[],
            items=[Item(codigo="A1", descripcion="Tornillo", cantidad=2.5, precio_unitario=40.0, subtotal_item=100.0)],
        )
    )
    respuesta_api = subir(cliente, FACTURA_A)
    assert respuesta_api.status_code == 200
    datos = respuesta_api.json()
    assert list(datos) == list(Factura.model_fields)
    Factura.model_validate(datos)
    assert datos["punto_venta"] == 3
    assert datos["items"][0]["cantidad"] == 2.5
    assert datos["impuestos"] == []
    assert datos["cuit_emisor"] is None
    assert len(claude.llamadas) == 1


def test_sin_sesion_responde_401_sin_llamar_a_claude(cliente, claude):
    respuesta_api = cliente.post("/extraer", files={"archivo": ("f.pdf", FACTURA_A)})
    assert respuesta_api.status_code == 401
    assert claude.llamadas == []


@pytest.mark.parametrize(
    "pdf",
    [
        generar_pdf(encabezado(letra="B", codigo="06")),
        generar_pdf(encabezado(), encabezado(numeracion="N° 0003-00009999")),
        generar_pdf(*[encabezado()] * 4),
        b"no soy un PDF",
    ],
    ids=["factura-b", "dos-facturas", "cuatro-paginas", "no-pdf"],
)
def test_pdf_fuera_de_alcance_no_llega_a_claude(cliente, claude, pdf):
    assert subir(cliente, pdf).status_code == 422
    assert claude.llamadas == []


def test_cantidad_de_archivos_distinta_de_1_responde_422(cliente, claude):
    archivos = [("archivo", ("a.pdf", FACTURA_A)), ("archivo", ("b.pdf", FACTURA_A))]
    respuesta_api = cliente.post("/extraer", files=archivos, headers=autorizacion(cliente, "ana"))
    assert respuesta_api.status_code == 422
    assert claude.llamadas == []


def test_fallo_de_claude_responde_502_con_mensaje(cliente, claude):
    claude.resultado = respuesta(None, "refusal")
    respuesta_api = subir(cliente, FACTURA_A)
    assert respuesta_api.status_code == 502
    assert respuesta_api.json() == {
        "detail": {"motivo": "fallo_extraccion", "mensaje": "No se pudo completar la extracción."}
    }


def test_respuesta_a_un_usuario_no_trae_datos_de_otro(cliente, claude):
    claude.resultado = respuesta(factura(razon_social_emisor="Proveedor de Ana"))
    assert subir(cliente, FACTURA_A, "ana").json()["razon_social_emisor"] == "Proveedor de Ana"
    claude.resultado = respuesta(factura(razon_social_emisor="Proveedor de Beto"))
    datos_beto = subir(cliente, FACTURA_A, "beto").json()
    assert "Proveedor de Ana" not in str(datos_beto)


def test_pdf_de_mas_de_1_mb_no_se_escribe_en_disco(cliente, monkeypatch):
    def escribir_en_disco(self):
        raise AssertionError("el archivo subido pasó a disco")

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", escribir_en_disco)
    grande = FACTURA_A + b"\n%" + b"x" * 2_000_000
    assert subir(cliente, grande).status_code == 200
