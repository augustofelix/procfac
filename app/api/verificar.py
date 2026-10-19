import sys
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app.api.auth import usuario_actual
from app.core.verificacion import Rechazo, verificar_pdf

router = APIRouter()

CANTIDAD_ARCHIVOS = Rechazo("cantidad_archivos", "Se debe enviar exactamente un archivo PDF.")


class _ParserEnMemoria(MultiPartParser):
    # Starlette pasa a un archivo temporal en disco las partes de más de 1 MB;
    # acá quedan siempre en memoria (RNF-07, AC-22)
    spool_max_size = sys.maxsize


async def leer_pdf_subido(request: Request) -> bytes:
    """Devuelve el contenido del único archivo de la petición (RNF-01, AC-19)."""
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise CANTIDAD_ARCHIVOS
    parser = _ParserEnMemoria(request.headers, request.stream(), max_files=2)
    try:
        formulario = await parser.parse()
    except MultiPartException:
        raise CANTIDAD_ARCHIVOS
    try:
        archivos = [valor for _, valor in formulario.multi_items() if isinstance(valor, UploadFile)]
        if len(archivos) != 1:
            raise CANTIDAD_ARCHIVOS
        return await archivos[0].read()
    finally:
        await formulario.close()


@router.post("/verificar", status_code=status.HTTP_204_NO_CONTENT)
async def verificar(
    # La sesión se valida antes de leer el archivo (RF-09, AC-05)
    usuario: Annotated[str, Depends(usuario_actual)],
    contenido: Annotated[bytes, Depends(leer_pdf_subido)],
) -> None:
    await run_in_threadpool(verificar_pdf, contenido)
