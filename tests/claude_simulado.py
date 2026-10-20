"""Un cliente de Claude simulado para los tests: ninguna prueba llama a la API real."""

import asyncio
from types import SimpleNamespace

import httpx2

from app.core.esquema import Factura

PETICION = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def factura(**campos) -> Factura:
    return Factura(**({campo: None for campo in Factura.model_fields} | campos))


def respuesta(parsed_output: Factura | None, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed_output)


class ClaudeSimulado:
    """Imita client.messages.parse: devuelve `resultado`, o lo lanza si es una excepción."""

    def __init__(self, resultado=None, demora: float = 0) -> None:
        self.resultado = resultado if resultado is not None else respuesta(factura())
        self.demora = demora
        self.llamadas: list[dict] = []
        self.messages = self

    async def parse(self, **parametros):
        self.llamadas.append(parametros)
        await asyncio.sleep(self.demora)
        if isinstance(self.resultado, BaseException):
            raise self.resultado
        return self.resultado
