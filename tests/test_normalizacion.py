import pytest

from app.core.esquema import Impuesto, Item
from app.core.normalizacion import normalizar
from tests.claude_simulado import factura


@pytest.mark.parametrize(
    ("cuit", "esperado"),
    [("30-12345678-9", "30123456789"), ("30 12345678 9", "30123456789"), ("30123456789", "30123456789"), ("-", None), (None, None)],
)
def test_cuit_solo_digitos(cuit, esperado):
    assert normalizar(factura(cuit_emisor=cuit, cuit_receptor=cuit)).cuit_receptor == esperado


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        ("2026-10-01", "2026-10-01"),
        ("01/10/2026", "2026-10-01"),
        ("01-10-2026", "2026-10-01"),
        ("01.10.2026", "2026-10-01"),
        ("31/02/2026", None),
        ("octubre", None),
        (None, None),
    ],
)
def test_fecha_iso(fecha, esperado):
    assert normalizar(factura(fecha_comprobante=fecha)).fecha_comprobante == esperado


@pytest.mark.parametrize(
    ("importe", "esperado"),
    [(100.005, 100.01), (121.0049, 121.0), (2.675, 2.68), (-1.005, -1.01), (3.0, 3.0), (None, None)],
)
def test_importes_a_2_decimales(importe, esperado):
    normalizada = normalizar(
        factura(
            subtotal=importe,
            total=importe,
            impuestos=[Impuesto(descripcion_impuesto="IVA 21%", importe=importe)],
            items=[Item(codigo="1", descripcion="x", cantidad=1, precio_unitario=importe, subtotal_item=importe)],
        )
    )
    assert normalizada.subtotal == normalizada.total == esperado
    assert normalizada.impuestos[0].importe == esperado
    assert normalizada.items[0].precio_unitario == normalizada.items[0].subtotal_item == esperado


def test_cantidad_sin_redondeo():
    item = Item(codigo="1", descripcion="x", cantidad=0.33333, precio_unitario=1, subtotal_item=1)
    assert normalizar(factura(items=[item])).items[0].cantidad == 0.33333


def test_textos_sin_espacios_sobrantes_y_vacios_en_null():
    normalizada = normalizar(factura(razon_social_emisor="  ACME SA ", localidad_emisor="   "))
    assert normalizada.razon_social_emisor == "ACME SA"
    assert normalizada.localidad_emisor is None


@pytest.mark.parametrize("lista", [None, []])
def test_listas_null_y_vacias_se_conservan(lista):
    normalizada = normalizar(factura(items=lista, impuestos=lista))
    assert normalizada.items == lista
    assert normalizada.impuestos == lista
