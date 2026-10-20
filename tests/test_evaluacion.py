import pytest

from tests.claude_simulado import factura
from tests.evaluacion import METRICAS, comparar, percentil_95

ITEMS = [
    {"codigo": "A1", "descripcion": "Tornillo", "cantidad": 2.5, "precio_unitario": 40.0, "subtotal_item": 100.0},
    {"codigo": "B2", "descripcion": "Tuerca", "cantidad": 10, "precio_unitario": 1.5, "subtotal_item": 15.0},
]
ESPERADA = factura(
    punto_venta=3,
    total=139.15,
    impuestos=[{"descripcion_impuesto": "IVA 21%", "importe": 24.15}, {"descripcion_impuesto": "Perc. IIBB", "importe": 0.0}],
    items=ITEMS,
).model_dump()


def test_factura_identica_acierta_todo():
    assert all(comparar(ESPERADA, ESPERADA).values())


def test_extraccion_fallida_no_acierta_nada():
    assert comparar(None, ESPERADA) == dict.fromkeys(METRICAS, False)


def test_campo_escalar_distinto():
    aciertos = comparar(ESPERADA | {"total": 139.16}, ESPERADA)
    assert aciertos["total"] is False
    assert aciertos["punto_venta"] is True


def test_impuestos_coinciden_sin_importar_el_orden():
    invertidos = ESPERADA | {"impuestos": list(reversed(ESPERADA["impuestos"]))}
    assert comparar(invertidos, ESPERADA)["impuestos"] is True


@pytest.mark.parametrize(
    "impuestos",
    [
        [{"descripcion_impuesto": "IVA 21 %", "importe": 24.15}, {"descripcion_impuesto": "Perc. IIBB", "importe": 0.0}],
        [{"descripcion_impuesto": "IVA 21%", "importe": 24.15}],
        None,
    ],
    ids=["texto-distinto", "falta-uno", "null"],
)
def test_impuestos_distintos(impuestos):
    assert comparar(ESPERADA | {"impuestos": impuestos}, ESPERADA)["impuestos"] is False


def test_cantidad_de_un_item_distinta_hace_incorrecta_la_factura():
    items = [ITEMS[0] | {"cantidad": 2}, ITEMS[1]]
    aciertos = comparar(ESPERADA | {"items": items}, ESPERADA)
    assert aciertos["cantidad_de_items"] is True
    assert aciertos["cantidad_de_cada_item"] is False
    assert aciertos["items.descripcion"] is True


def test_otra_cantidad_de_items_hace_incorrectos_todos_los_campos_de_items():
    aciertos = comparar(ESPERADA | {"items": ITEMS[:1]}, ESPERADA)
    assert aciertos["cantidad_de_items"] is False
    assert aciertos["cantidad_de_cada_item"] is False
    assert all(aciertos[f"items.{c}"] is False for c in ("codigo", "descripcion", "precio_unitario", "subtotal_item"))


def test_items_se_comparan_por_posicion():
    aciertos = comparar(ESPERADA | {"items": list(reversed(ITEMS))}, ESPERADA)
    assert aciertos["cantidad_de_items"] is True
    assert aciertos["items.codigo"] is False


def test_percentil_95_por_rango_mas_cercano():
    tiempos = [float(n) for n in range(1, 21)]
    assert percentil_95(tiempos) == 19.0
    assert percentil_95([5.0]) == 5.0
