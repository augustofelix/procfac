import configparser
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
RUTA_CONFIG = RAIZ / "config.ini"
RUTA_ENV = RAIZ / ".env"


@lru_cache
def cargar_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config.read(RUTA_CONFIG, encoding="utf-8"):
        raise FileNotFoundError(f"No se encontró {RUTA_CONFIG}")
    return config


@lru_cache
def cargar_entorno() -> None:
    """Carga usuarios, contraseñas y API key de Claude desde .env, fuera del repositorio."""
    load_dotenv(RUTA_ENV)
