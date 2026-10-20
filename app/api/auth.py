import os
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import cargar_entorno
from app.core.sesiones import Sesiones
from app.core.usuarios import cargar_usuarios, credenciales_validas

router = APIRouter()
_sesiones = Sesiones()
_bearer = HTTPBearer(auto_error=False)


@lru_cache
def obtener_usuarios() -> dict[str, str]:
    cargar_entorno()
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


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    sesiones: Annotated[Sesiones, Depends(obtener_sesiones)],
) -> str:
    """Exige un token de sesión válido; si no, responde 401 (RF-09, AC-05)."""
    usuario = sesiones.usuario(credenciales.credentials) if credenciales else None
    if usuario is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sesión no iniciada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
