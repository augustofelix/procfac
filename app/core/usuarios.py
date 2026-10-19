import hmac
from collections.abc import Mapping

MAX_USUARIOS = 5


def cargar_usuarios(entorno: Mapping[str, str]) -> dict[str, str]:
    """Devuelve {usuario: contraseña} desde APP_USER_n / APP_PASSWORD_n (RF-19, RNF-04)."""
    usuarios: dict[str, str] = {}
    for n in range(1, MAX_USUARIOS + 1):
        usuario = entorno.get(f"APP_USER_{n}", "").strip()
        contrasena = entorno.get(f"APP_PASSWORD_{n}", "")
        if not usuario and not contrasena:
            continue
        if not usuario or not contrasena:
            raise ValueError(f"APP_USER_{n} y APP_PASSWORD_{n} deben definirse juntos")
        if usuario in usuarios:
            raise ValueError(f"El usuario {usuario!r} está repetido en .env")
        usuarios[usuario] = contrasena
    return usuarios


def credenciales_validas(usuarios: Mapping[str, str], usuario: str, contrasena: str) -> bool:
    esperada = usuarios.get(usuario)
    if esperada is None:
        return False
    return hmac.compare_digest(esperada.encode(), contrasena.encode())
