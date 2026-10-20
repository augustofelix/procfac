import pytest

from app.core.verificacion import Rechazo, codigo_comprobante, numeracion, verificar_pdf
from tests.pdfs import FACTURA_A, factura, generar_pdf


def motivo_de_rechazo(contenido: bytes) -> str | None:
    try:
        verificar_pdf(contenido, max_paginas=3)
    except Rechazo as rechazo:
        return rechazo.motivo
    return None


def test_factura_a_se_acepta():
    assert motivo_de_rechazo(FACTURA_A) is None


def test_original_duplicado_y_triplicado_cuentan_como_una_factura():
    pdf = generar_pdf(factura("ORIGINAL"), factura("DUPLICADO"), factura("TRIPLICADO"))
    assert motivo_de_rechazo(pdf) is None


def test_factura_de_varias_paginas_se_acepta():
    pdf = generar_pdf(factura(), ["Detalle (continuación)", "Ítem 31"])
    assert motivo_de_rechazo(pdf) is None


@pytest.mark.parametrize(
    "contenido",
    [b"", b"hola", b"PK\x03\x04 un zip", b"%PDF-1.4 basura"],
    ids=["vacio", "texto", "zip", "pdf-corrupto"],
)
def test_no_pdf_se_rechaza(contenido):
    assert motivo_de_rechazo(contenido) == "no_es_pdf"


def test_mas_de_3_paginas_se_rechaza():
    pdf = generar_pdf(factura(), factura("DUPLICADO"), factura("TRIPLICADO"), factura("CUADRUPLICADO"))
    assert motivo_de_rechazo(pdf) == "demasiadas_paginas"


@pytest.mark.parametrize(
    "paginas",
    [
        [factura(), factura(numeracion="Punto de Venta: 00003 Comp. Nro: 00001235")],
        [factura(), factura(numeracion="Punto de Venta: 00004 Comp. Nro: 00001234")],
        [factura(numeracion="N° 0003-00001234"), factura(numeracion="N° 0003-00009999")],
        [factura(), factura(letra="B", codigo="06", numeracion="Punto de Venta: 00001 Comp. Nro: 00000077")],
    ],
    ids=["otro-numero", "otro-punto-de-venta", "formato-guion", "factura-a-y-b"],
)
def test_mas_de_una_factura_se_rechaza(paginas):
    assert motivo_de_rechazo(generar_pdf(*paginas)) == "mas_de_una_factura"


@pytest.mark.parametrize(
    "lineas",
    [
        factura(titulo="NOTA DE CRÉDITO", codigo="03"),
        factura(titulo="NOTA DE DÉBITO", codigo="02"),
        factura(titulo="RECIBO", codigo="04"),
        factura(titulo="REMITO", letra="R", codigo="91"),
        factura(titulo="LIQUIDACIÓN", codigo="63"),
        factura(letra="M", codigo="51"),
        factura(titulo="FACTURA DE CRÉDITO ELECTRÓNICA MiPyMEs (FCE)", codigo="201"),
        factura(letra="B", codigo="06"),
        factura(letra="C", codigo="11"),
        factura(letra="E", codigo="19"),
        ["COMPROBANTE", "X", "Documento no válido como factura"],
        ["Un documento cualquiera"],
        ["COD. 01", "Comprobante sin título"],
    ],
    ids=[
        "nota-credito", "nota-debito", "recibo", "remito", "liquidacion", "factura-m",
        "fce-mipyme-a", "factura-b", "factura-c", "factura-e", "comprobante-x",
        "tipo-no-identificable", "sin-palabra-factura",
    ],
)
def test_comprobante_fuera_de_alcance_se_rechaza(lineas):
    assert motivo_de_rechazo(generar_pdf(lineas)) == "no_factura_a"


def test_factura_a_sin_codigo_con_letra_a_se_acepta():
    pdf = generar_pdf(["A", "Comprobante: 0012 - 00075812", "Total Factura: $ 45,500.01"])
    assert motivo_de_rechazo(pdf) is None


@pytest.mark.parametrize(
    "lineas",
    [
        ["B", "Total Factura: $ 100.00"],
        ["A", "Total: $ 100.00"],
        ["A", "NOTA DE CRÉDITO", "Factura asociada: 0012-00075812"],
        ["A", "NOTA DE DÉBITO", "Factura asociada: 0012-00075812"],
        ["A", "RECIBO", "Cancela factura 0012-00075812"],
        ["A", "REMITO", "Factura 0012-00075812"],
        ["A", "LIQUIDACIÓN", "Factura 0012-00075812"],
        ["A", "FACTURA DE CRÉDITO ELECTRÓNICA MiPyMEs (FCE)"],
    ],
    ids=["letra-b", "sin-palabra-factura", "nota-credito", "nota-debito", "recibo", "remito", "liquidacion", "fce"],
)
def test_comprobante_sin_codigo_fuera_de_alcance_se_rechaza(lineas):
    assert motivo_de_rechazo(generar_pdf(lineas)) == "no_factura_a"


def test_con_codigo_distinto_de_01_no_alcanza_la_letra_a():
    assert motivo_de_rechazo(generar_pdf(["A", "FACTURA", "COD. 06"])) == "no_factura_a"


def test_pdf_protegido_con_contrasena_se_rechaza():
    assert motivo_de_rechazo(generar_pdf(factura(), contrasena="secreta")) == "no_factura_a"


def test_pdf_escaneado_sin_texto_se_rechaza():
    assert motivo_de_rechazo(generar_pdf([], [])) == "no_factura_a"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("COD. 01", 1),
        ("Cód. 01", 1),
        ("CODIGO N° 01", 1),
        ("Código Nº: 01", 1),
        ("Cod. 1", 1),
        ("Código N° 1", 1),
        ("Código Nro001 Factura", 1),
        ("A\n01 FACTURA", 1),
        ("COD.201", 201),
        ("201 FACTURA DE CRÉDITO ELECTRÓNICA", 201),
        ("Código Pago Electrónico", None),
        ("Codigo: ceac96991", None),
        ("Código 1234567", None),
        ("Total Factura: $ 45,500.01", None),
        ("Hola", None),
    ],
)
def test_codigo_comprobante(texto, esperado):
    assert codigo_comprobante(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Punto de Venta: 00003 Comp. Nro: 00001234", (3, 1234)),
        ("N° 0003-00001234", (3, 1234)),
        ("Nro. 00012 - 00000001", (12, 1)),
        ("CUIT: 30-12345678-9", None),
    ],
)
def test_numeracion(texto, esperado):
    assert numeracion(texto) == esperado
