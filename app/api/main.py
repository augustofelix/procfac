import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import auth, extraer, verificar
from app.core.extraccion import FalloExtraccion
from app.core.verificacion import Rechazo

log = logging.getLogger(__name__)

app = FastAPI(title="procfac")
app.include_router(auth.router)
app.include_router(verificar.router)
app.include_router(extraer.router)


@app.exception_handler(Rechazo)
async def responder_rechazo(request: Request, rechazo: Rechazo) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": {"motivo": rechazo.motivo, "mensaje": rechazo.mensaje}},
    )


@app.exception_handler(FalloExtraccion)
async def responder_fallo_extraccion(request: Request, fallo: FalloExtraccion) -> JSONResponse:
    # El motivo técnico queda en el log del servidor, sin contenido de la factura
    log.warning("Falló la extracción: %s", fallo)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": {"motivo": "fallo_extraccion", "mensaje": "No se pudo completar la extracción."}},
    )
