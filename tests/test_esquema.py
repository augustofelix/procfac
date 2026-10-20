import pytest
from pydantic import ValidationError

from app.core.esquema import Factura, campos_no_obtenidos, nada_obtenido
from tests.claude_simulado import factura


def test_todos_los_campos_son_obligatorios_y_admiten_null():
    esquema = Factura.model_json_schema()
    assert esquema["required"] == list(Factura.model_fields)
    assert esquema["additionalProperties"] is False
    with pytest.raises(ValidationError):
        Factura(punto_venta=1)


def test_campos_no_obtenidos_son_los_null():
    parcial = factura(punto_venta=3, total=10.0, items=[], impuestos=None)
    no_obtenidos = campos_no_obtenidos(parcial)
    assert "punto_venta" not in no_obtenidos
    assert "items" not in no_obtenidos  # lista vacía: el comprobante no tiene ítems
    assert "impuestos" in no_obtenidos
    assert len(no_obtenidos) == len(Factura.model_fields) - 3


@pytest.mark.parametrize(
    ("campos", "esperado"),
    [
        ({}, True),
        ({"items": [], "impuestos": []}, True),
        ({"items": None, "impuestos": []}, True),
        ({"total": 0.0}, False),
        ({"condicion_venta": "Contado"}, False),
    ],
)
def test_nada_obtenido(campos, esperado):
    assert nada_obtenido(factura(**campos)) is esperado
