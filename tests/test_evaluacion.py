import json

import pytest

from tests.claude_simulado import factura
from tests.evaluacion import METRICAS, _conjunto, comparar, percentil_95

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


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    import tests.evaluacion as evaluacion

    for nombre in ("01.PDF", "02.pdf", "03.PDF"):
        (tmp_path / nombre).write_bytes(b"%PDF-1.4")
    for nombre in ("01.json", "02.json"):
        (tmp_path / nombre).write_text(json.dumps(ESPERADA), encoding="utf-8")
    monkeypatch.setattr(evaluacion, "CARPETA", tmp_path)
    return tmp_path


def test_sin_pdf_elegidos_usa_todos_los_que_tienen_json(carpeta):
    assert [pdf.name for pdf, _ in _conjunto()] == ["01.PDF", "02.pdf"]


@pytest.mark.parametrize("nombre", ["01", "01.PDF", "01.pdf"])
def test_elige_un_pdf_con_o_sin_extension(carpeta, nombre):
    conjunto = _conjunto([nombre])
    assert [pdf.name for pdf, _ in conjunto] == ["01.PDF"]
    assert conjunto[0][1] == ESPERADA


def test_elige_varios_pdf_en_el_orden_pedido(carpeta):
    assert [pdf.name for pdf, _ in _conjunto(["02", "01"])] == ["02.pdf", "01.PDF"]


def test_pdf_inexistente_corta_con_mensaje(carpeta):
    with pytest.raises(SystemExit, match="No existe 99"):
        _conjunto(["99"])


def test_pdf_sin_json_esperado_corta_con_mensaje(carpeta):
    with pytest.raises(SystemExit, match="Falta el JSON esperado 03.json"):
        _conjunto(["03"])


@pytest.mark.parametrize(
    ("obtenido", "esperado", "motivo"),
    [
        ("ACME SA", "ACME SA", None),
        ("ACME  sa ", "ACME SA", "difieren solo en mayúsculas o espacios"),
        ("IVA Responsable Inscripto", "Responsable Inscripto", "lo obtenido tiene texto de más"),
        ("Lobos", "Lobos, Buenos Aires", "lo obtenido tiene texto de menos"),
        ("Otra cosa", "ACME SA", "texto distinto"),
        (None, "ACME SA", "esperado con dato, obtenido null"),
        ("ACME SA", None, "esperado null, obtenido con dato"),
        (10.0, 10, None),
        (10.5, 10, "número distinto"),
        ("10", 10, "tipo distinto"),
    ],
)
def test_clasificar_diferencias(obtenido, esperado, motivo):
    from tests.evaluacion import _clasificar

    assert _clasificar(obtenido, esperado) == motivo


def test_diferencias_sin_mostrar_valores():
    from tests.evaluacion import diferencias

    obtenida = ESPERADA | {
        "total": 1.0,
        "impuestos": [{"descripcion_impuesto": "IVA 21 %", "importe": 24.15}],
        "items": [ITEMS[0] | {"descripcion": "TORNILLO"}, ITEMS[1], ITEMS[1]],
    }
    lineas = diferencias(obtenida, ESPERADA)
    assert lineas == [
        "total: número distinto",
        "impuestos: esperados 2, obtenidos 1",
        "impuestos[1].descripcion_impuesto: difieren solo en mayúsculas o espacios",
        "items: esperados 2, obtenidos 3",
        "items[1].descripcion: difieren solo en mayúsculas o espacios",
    ]
    assert not any("Tornillo" in linea or "139" in linea for linea in lineas)


def test_diferencias_de_impuestos_sin_importar_el_orden():
    from tests.evaluacion import diferencias

    iva, percepcion = ESPERADA["impuestos"]
    obtenida = ESPERADA | {"impuestos": [percepcion | {"importe": 1.0}, iva]}
    assert diferencias(obtenida, ESPERADA) == ["impuestos[1].importe: número distinto"]
    assert diferencias(ESPERADA | {"impuestos": [percepcion, iva]}, ESPERADA) == []
