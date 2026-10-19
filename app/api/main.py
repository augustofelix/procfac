from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import auth, verificar
from app.core.verificacion import Rechazo

app = FastAPI(title="procfac")
app.include_router(auth.router)
app.include_router(verificar.router)


@app.exception_handler(Rechazo)
async def responder_rechazo(request: Request, rechazo: Rechazo) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": {"motivo": rechazo.motivo, "mensaje": rechazo.mensaje}},
    )
