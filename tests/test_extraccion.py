import asyncio
import base64

import anthropic
import httpx2
import pytest
from pydantic import ValidationError

from app.api.extraer import obtener_extractor
from app.core.esquema import Factura, FacturaExtraida, Item
from app.core.extraccion import Extractor, FalloExtraccion
from tests.claude_simulado import PETICION, ClaudeSimulado, factura, respuesta
from tests.pdfs import FACTURA_A


def extraer(claude: ClaudeSimulado, timeout: float = 5) -> Factura:
    return asyncio.run(Extractor(claude, "claude-opus-5-5", "low", timeout).extraer(FACTURA_A))


def test_envia_el_pdf_como_documento_con_el_esquema_de_salida():
    claude = ClaudeSimulado()
    extraer(claude)
    assert len(claude.llamadas) == 1
    parametros = claude.llamadas[0]
    assert parametros["model"] == "claude-opus-5-5"
    assert parametros["output_config"] == {"effort": "low"}
    assert parametros["output_format"] is FacturaExtraida
    documento = parametros["messages"][0]["content"][0]
    assert documento["type"] == "document"
    assert documento["source"]["media_type"] == "application/pdf"
    assert base64.standard_b64decode(documento["source"]["data"]) == FACTURA_A


def test_devuelve_la_factura_normalizada():
    extraida = factura(
        cuit_emisor="30-12345678-9",
        fecha_comprobante="01/10/2026",
        total=121.005,
        items=[Item(codigo="A1", descripcion="Tornillo", cantidad=2.5, precio_unitario=40.0, subtotal_item=100.0)],
    )
    resultado = extraer(ClaudeSimulado(respuesta(extraida)))
    assert resultado.cuit_emisor == "30123456789"
    assert resultado.fecha_comprobante == "2026-10-01"
    assert resultado.total == 121.01
    assert resultado.items[0].cantidad == 2.5


def error_de_estado(codigo: int) -> anthropic.APIStatusError:
    return anthropic.APIStatusError("error", response=httpx2.Response(codigo, request=PETICION), body=None)


@pytest.mark.parametrize(
    "error",
    [
        error_de_estado(500),
        error_de_estado(529),
        error_de_estado(400),
        error_de_estado(429),
        anthropic.APIConnectionError(request=PETICION),
        anthropic.APITimeoutError(request=PETICION),
        ValidationError.from_exception_data("Factura", []),
        ValueError("JSON inválido"),
        RuntimeError("inesperado"),
    ],
    ids=["500", "529", "400", "429", "conexion", "timeout-sdk", "esquema", "json", "inesperado"],
)
def test_error_de_claude_es_fallo_sin_reintentar(error):
    claude = ClaudeSimulado(error)
    with pytest.raises(FalloExtraccion):
        extraer(claude)
    assert len(claude.llamadas) == 1


def test_sin_respuesta_dentro_del_timeout_es_fallo():
    claude = ClaudeSimulado(demora=1)
    with pytest.raises(FalloExtraccion, match="no respondió"):
        extraer(claude, timeout=0.05)


@pytest.mark.parametrize(
    "incompleta",
    [respuesta(None, "refusal"), respuesta(factura(), "max_tokens"), respuesta(None)],
    ids=["refusal", "max-tokens", "sin-salida"],
)
def test_respuesta_incompleta_es_fallo(incompleta):
    with pytest.raises(FalloExtraccion):
        extraer(ClaudeSimulado(incompleta))


def test_cliente_real_sin_reintentos_y_con_timeout_de_config():
    obtener_extractor.cache_clear()
    try:
        extractor = obtener_extractor()
        assert extractor.cliente.max_retries == 0
        assert extractor.cliente.timeout == 60
        assert extractor.timeout == 60
        assert extractor.modelo == "claude-opus-5-5"
    finally:
        obtener_extractor.cache_clear()


def _uniones(esquema: dict) -> int:
    """Propiedades con anyOf o lista de tipos, en el objeto y en sus $defs."""
    objetos = [esquema, *esquema.get("$defs", {}).values()]
    return sum(
        "anyOf" in propiedad or isinstance(propiedad.get("type"), list)
        for objeto in objetos
        for propiedad in objeto.get("properties", {}).values()
    )


def test_esquema_pedido_a_claude_respeta_el_limite_de_uniones():
    # La salida estructurada de la API rechaza con 400 más de 16 campos con unión
    assert _uniones(FacturaExtraida.model_json_schema()) <= 16
    assert list(FacturaExtraida.model_fields) == list(Factura.model_fields)


def test_textos_vacios_de_claude_pasan_a_null():
    textos = {campo: "" for campo, info in FacturaExtraida.model_fields.items() if info.annotation is str}
    numeros = {"punto_venta": 3, "numero_comprobante": None, "subtotal": None, "total": 10.0}
    extraida = FacturaExtraida(
        **textos,
        **numeros,
        impuestos=[{"descripcion_impuesto": "", "importe": 1.0}],
        items=[{"codigo": "", "descripcion": "Tornillo", "cantidad": 1, "precio_unitario": None, "subtotal_item": 2.0}],
    )
    resultado = extraer(ClaudeSimulado(respuesta(extraida)))
    assert all(getattr(resultado, campo) is None for campo in textos)
    assert resultado.punto_venta == 3
    assert resultado.impuestos[0].descripcion_impuesto is None
    assert resultado.items[0].codigo is None
    assert resultado.items[0].descripcion == "Tornillo"
