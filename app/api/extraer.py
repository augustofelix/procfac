from functools import lru_cache
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.api.auth import usuario_actual
from app.api.verificar import MAX_PAGINAS, leer_pdf_subido
from app.core.config import cargar_config, cargar_entorno
from app.core.esquema import Factura
from app.core.extraccion import Extractor
from app.core.verificacion import verificar_pdf

router = APIRouter()


@lru_cache
def obtener_extractor() -> Extractor:
    cargar_entorno()
    claude = cargar_config()["claude"]
    timeout = claude.getfloat("timeout_segundos")
    # Sin reintentos automáticos del SDK (RF-27)
    cliente = anthropic.AsyncAnthropic(timeout=timeout, max_retries=0)
    return Extractor(cliente, claude["model"], claude["effort"], timeout)


@router.post("/extraer")
async def extraer(
    # La sesión se valida antes de leer el archivo (RF-09, AC-05)
    usuario: Annotated[str, Depends(usuario_actual)],
    contenido: Annotated[bytes, Depends(leer_pdf_subido)],
    extractor: Annotated[Extractor, Depends(obtener_extractor)],
) -> Factura:
    # Los mismos filtros de /verificar: nada fuera de alcance llega a Claude (RF-18, RF-24, RF-28)
    await run_in_threadpool(verificar_pdf, contenido, MAX_PAGINAS)
    # Los campos extraídos vuelven en esta misma respuesta (RNF-06, AC-17)
    return await extractor.extraer(contenido)
