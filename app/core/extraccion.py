import asyncio
import base64
import logging

import anthropic
from pydantic import ValidationError

from app.core.esquema import Factura, FacturaExtraida
from app.core.normalizacion import normalizar

log = logging.getLogger(__name__)

INSTRUCCIONES = """\
Extraé los datos de la factura A argentina del PDF adjunto con el esquema JSON indicado.

Reglas:
- Emisor es quien emite la factura (encabezado); receptor es el cliente al que se le factura.
- Copiá los textos tal como figuran en el PDF (razón social, domicilio, localidad, \
condición frente al IVA, condición de venta, descripciones de ítems e impuestos), \
sin corregirlos ni completarlos.
- Si un campo no figura en el comprobante o no se puede leer, devolvé "" (cadena vacía) \
si es de texto o null si es numérico. No inventes valores.
- items e impuestos: null si no se pudieron leer; [] si el comprobante no tiene ninguno.
- Si el PDF trae las copias ORIGINAL, DUPLICADO y TRIPLICADO de la misma factura, \
tomá los datos de una sola copia: no repitas los ítems.
- punto_venta y numero_comprobante: enteros sin ceros a la izquierda.
- cuit_emisor y cuit_receptor: 11 dígitos, sin guiones ni espacios.
- fecha_comprobante: fecha de emisión en formato AAAA-MM-DD.
- Importes y cantidades: números con punto decimal, sin separador de miles ni símbolo de moneda.
- subtotal: el subtotal del pie del comprobante, antes de impuestos. total: el importe total.
- impuestos: un elemento por cada impuesto o percepción del pie (por ejemplo IVA 21%), \
con descripcion_impuesto tal como figura y su importe. No incluyas el subtotal ni el total.
- items: un elemento por cada línea del detalle, en el orden del comprobante, con codigo, \
descripcion, cantidad, precio_unitario y subtotal_item tal como figuran.
"""


class FalloExtraccion(Exception):
    """La API de Claude falló: error, sin respuesta a tiempo o respuesta inválida (RF-26)."""


class Extractor:
    def __init__(self, cliente: anthropic.AsyncAnthropic, modelo: str, esfuerzo: str, timeout: float) -> None:
        self.cliente = cliente
        self.modelo = modelo
        self.esfuerzo = esfuerzo
        self.timeout = timeout

    async def extraer(self, contenido: bytes) -> Factura:
        """Una sola llamada a Claude, sin reintentos (RNF-06, RF-27)."""
        documento = base64.standard_b64encode(contenido).decode()
        try:
            async with asyncio.timeout(self.timeout):
                respuesta = await self.cliente.messages.parse(
                    model=self.modelo,
                    max_tokens=16000,
                    system=INSTRUCCIONES,
                    output_config={"effort": self.esfuerzo},
                    output_format=FacturaExtraida,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {"type": "base64", "media_type": "application/pdf", "data": documento},
                                },
                                {"type": "text", "text": "Extraé los datos de esta factura."},
                            ],
                        }
                    ],
                )
        except (TimeoutError, anthropic.APITimeoutError) as error:
            raise FalloExtraccion(f"Claude no respondió en {self.timeout:g} segundos") from error
        except anthropic.APIStatusError as error:
            raise FalloExtraccion(f"Claude devolvió HTTP {error.status_code} ({error.request_id})") from error
        except anthropic.APIConnectionError as error:
            raise FalloExtraccion("No se pudo conectar con la API de Claude") from error
        except (ValidationError, ValueError) as error:
            raise FalloExtraccion("La respuesta de Claude no cumple el Esquema de salida") from error
        except Exception as error:
            raise FalloExtraccion(f"Error inesperado al llamar a Claude: {type(error).__name__}") from error
        if respuesta.stop_reason != "end_turn" or respuesta.parsed_output is None:
            # refusal o max_tokens: la salida puede no cumplir el esquema
            raise FalloExtraccion(f"Respuesta de Claude incompleta (stop_reason={respuesta.stop_reason})")
        return normalizar(respuesta.parsed_output)
