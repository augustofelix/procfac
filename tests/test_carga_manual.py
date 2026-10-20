import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.core.esquema import Factura
from tests.carga_manual import NUEVA, preparar
from tests.pdfs import FACTURA_A

RUTA = str(Path(__file__).resolve().parent / "carga_manual.py")


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    """Una carpeta temporal con un PDF sintético: los tests nunca tocan tests/data/."""
    (tmp_path / "01.PDF").write_bytes(FACTURA_A)
    monkeypatch.setenv("PROCFAC_CARPETA_PDF", str(tmp_path))
    return tmp_path


def abrir():
    return AppTest.from_file(RUTA, default_timeout=30).run()


def campo(at, etiqueta):
    return next(w for w in [*at.text_input, *at.number_input] if w.label == etiqueta)


def test_preparar_normaliza_como_la_extraccion():
    datos, errores = preparar(NUEVA | {"cuit_emisor": "30-12345678-9", "fecha_comprobante": "01/10/2026", "total": 121.005})
    assert errores == []
    assert datos["cuit_emisor"] == "30123456789"
    assert datos["fecha_comprobante"] == "2026-10-01"
    assert datos["total"] == 121.01


@pytest.mark.parametrize(
    ("valores", "error"),
    [
        ({"cuit_receptor": "30-123"}, "cuit_receptor debe tener 11 dígitos"),
        ({"fecha_comprobante": "31/02/2026"}, "fecha_comprobante no es una fecha válida (AAAA-MM-DD o DD/MM/AAAA)"),
    ],
)
def test_preparar_rechaza_formatos_invalidos(valores, error):
    datos, errores = preparar(NUEVA | valores)
    assert datos is None
    assert errores == [error]


def test_sin_pdf_avisa(tmp_path, monkeypatch):
    monkeypatch.setenv("PROCFAC_CARPETA_PDF", str(tmp_path))
    assert abrir().info[0].value == f"No hay PDF en {tmp_path}"


def test_muestra_el_pdf_y_los_campos(carpeta):
    at = abrir()
    assert not at.exception
    assert at.selectbox[0].options == ["—  01.PDF"]
    assert len(at.get("image")) == 1
    assert len(at.text_input) + len(at.number_input) == len(Factura.model_fields) - 2


def test_guarda_el_json_al_lado_del_pdf(carpeta):
    at = abrir()
    campo(at, "Punto de venta").set_value(3)
    campo(at, "Razón social").input("ACME SA")
    campo(at, "Fecha (AAAA-MM-DD)").input("01/10/2026")
    at.button[0].click().run()
    assert at.success[0].value == "Guardado 01.json"
    datos = json.loads((carpeta / "01.json").read_text(encoding="utf-8"))
    assert list(datos) == list(Factura.model_fields)
    assert datos["punto_venta"] == 3
    assert datos["razon_social_emisor"] == "ACME SA"
    assert datos["fecha_comprobante"] == "2026-10-01"
    assert datos["cuit_emisor"] is None
    assert datos["items"] == []
    assert datos["impuestos"] == []


def test_reabre_el_json_existente_para_editarlo(carpeta):
    guardado = NUEVA | {"punto_venta": 7, "condicion_venta": "Contado"}
    (carpeta / "01.json").write_text(json.dumps(guardado), encoding="utf-8")
    at = abrir()
    assert at.selectbox[0].options == ["✔  01.PDF"]
    assert campo(at, "Punto de venta").value == 7
    assert campo(at, "Condición de venta").value == "Contado"
    assert at.button[0].label == "Guardar JSON (reemplaza el actual)"


def test_json_existente_invalido_se_muestra_vacio(carpeta):
    (carpeta / "01.json").write_text("{no es json", encoding="utf-8")
    at = abrir()
    assert "no cumple el Esquema de salida" in at.warning[0].value
    assert campo(at, "Punto de venta").value is None


def test_no_guarda_con_errores(carpeta):
    at = abrir()
    next(w for w in at.text_input if w.label == "CUIT").input("30-123")
    at.button[0].click().run()
    assert "cuit_emisor debe tener 11 dígitos" in at.error[0].value
    assert not (carpeta / "01.json").exists()
