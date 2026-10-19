import configparser
from functools import lru_cache
from pathlib import Path

RUTA_CONFIG = Path(__file__).resolve().parents[2] / "config.ini"


@lru_cache
def cargar_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config.read(RUTA_CONFIG, encoding="utf-8"):
        raise FileNotFoundError(f"No se encontró {RUTA_CONFIG}")
    return config
