import asyncio
import base64

import anthropic
import httpx2
import pytest
from pydantic import ValidationError

from app.api.extraer import obtener_extractor
from app.core.esquema import Factura, Item
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
    assert parametros["output_format"] is Factura
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
