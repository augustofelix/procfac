import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.sesiones import Sesiones
from app.core.usuarios import cargar_usuarios, credenciales_validas

RUTA_ENV = Path(__file__).resolve().parents[2] / ".env"

router = APIRouter()
_sesiones = Sesiones()


@lru_cache
def obtener_usuarios() -> dict[str, str]:
    load_dotenv(RUTA_ENV)
    return cargar_usuarios(os.environ)


def obtener_sesiones() -> Sesiones:
    return _sesiones


class Credenciales(BaseModel):
    usuario: str
    contrasena: str


class Sesion(BaseModel):
    token: str


@router.post("/login")
def login(
    credenciales: Credenciales,
    usuarios: Annotated[dict[str, str], Depends(obtener_usuarios)],
    sesiones: Annotated[Sesiones, Depends(obtener_sesiones)],
) -> Sesion:
    if not credenciales_validas(usuarios, credenciales.usuario, credenciales.contrasena):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")
    return Sesion(token=sesiones.crear(credenciales.usuario))
