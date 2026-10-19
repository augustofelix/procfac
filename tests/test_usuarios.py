import pytest

from app.core.usuarios import cargar_usuarios, credenciales_validas


def test_carga_usuarios_definidos_y_saltea_huecos():
    entorno = {
        "APP_USER_1": "ana",
        "APP_PASSWORD_1": "clave-ana",
        "APP_USER_3": "beto",
        "APP_PASSWORD_3": "clave-beto",
    }
    assert cargar_usuarios(entorno) == {"ana": "clave-ana", "beto": "clave-beto"}


def test_admite_hasta_5_usuarios():
    entorno = {}
    for n in range(1, 7):
        entorno[f"APP_USER_{n}"] = f"u{n}"
        entorno[f"APP_PASSWORD_{n}"] = f"p{n}"
    assert list(cargar_usuarios(entorno)) == ["u1", "u2", "u3", "u4", "u5"]


def test_usuario_sin_contrasena_es_error():
    with pytest.raises(ValueError):
        cargar_usuarios({"APP_USER_1": "ana"})


def test_usuario_repetido_es_error():
    entorno = {
        "APP_USER_1": "ana",
        "APP_PASSWORD_1": "a",
        "APP_USER_2": "ana",
        "APP_PASSWORD_2": "b",
    }
    with pytest.raises(ValueError):
        cargar_usuarios(entorno)


@pytest.mark.parametrize(
    ("usuario", "contrasena", "esperado"),
    [
        ("ana", "clave-ana", True),
        ("ana", "otra", False),
        ("nadie", "clave-ana", False),
        ("ANA", "clave-ana", False),
    ],
)
def test_credenciales_validas(usuario, contrasena, esperado):
    assert credenciales_validas({"ana": "clave-ana"}, usuario, contrasena) is esperado
