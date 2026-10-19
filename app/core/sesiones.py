import secrets
import threading


class Sesiones:
    """Tokens de sesión en memoria, sin cierre ni vencimiento (fuera del alcance del MVP)."""

    def __init__(self) -> None:
        self._usuarios: dict[str, str] = {}
        self._lock = threading.Lock()

    def crear(self, usuario: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._usuarios[token] = usuario
        return token

    def usuario(self, token: str) -> str | None:
        with self._lock:
            return self._usuarios.get(token)
