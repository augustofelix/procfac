import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.core.esquema import Factura
from app.ui.validacion import armar_json
from tests.pdfs import FACTURA_A

RUTA_UI = str(Path(__file__).resolve().parents[1] / "app" / "ui" / "main.py")

VACIA = {campo: None for campo in Factura.model_fields}
PARCIAL = VACIA | {
    "punto_venta": 3,
    "numero_comprobante": 1234,
    "razon_social_emisor": "ACMR SA",
    "fecha_comprobante": "2026-10-01",
    "total": 121.0,
    "impuestos": [{"descripcion_impuesto": "IVA 21%", "importe": 21.0}],
    "items": [],
}


def respuesta(status_code, json=None):
    return httpx.Response(status_code, json=json, request=httpx.Request("POST", "http://test/extraer"))


def extraer(respuesta_backend=None, error=None):
    """La UI después de aceptar el consentimiento, con /extraer simulado."""
    at = AppTest.from_file(RUTA_UI)
    at.session_state.token = "t"
    at.session_state.usuario = "ana"
    at.session_state.pdf = ("factura.pdf", FACTURA_A)
    at.session_state.consentimiento = True
    with patch("httpx.post", return_value=respuesta_backend, side_effect=error) as post:
        at.run()
    return at, post


def campo(at, etiqueta):
    return next(w for w in [*at.text_input, *at.number_input] if w.label == etiqueta)


def boton(at, etiqueta):
    return next(b for b in at.button if b.label == etiqueta)


def test_muestra_todos_los_campos_extraidos():
    at, post = extraer(respuesta(200, PARCIAL))
    assert post.call_count == 1
    assert post.call_args.args[0].endswith("/extraer")
    assert at.subheader[0].value == "Validar campos"
    assert campo(at, "Punto de venta").value == 3
    assert campo(at, "Número de comprobante").value == 1234
    assert campo(at, "Fecha (AAAA-MM-DD)").value == "2026-10-01"
    assert campo(at, "Total").value == 121.0
    # 16 campos simples más las tablas de ítems e impuestos
    assert len(at.text_input) + len(at.number_input) == len(Factura.model_fields) - 2
    assert len(at.get("dataframe")) == 2


def test_indica_exactamente_los_campos_no_obtenidos():
    at, _ = extraer(respuesta(200, PARCIAL))
    marcados = [w.label for w in [*at.text_input, *at.number_input] if w.label.endswith("— no obtenido")]
    no_obtenidos = [c for c, v in PARCIAL.items() if v is None and c not in ("items", "impuestos")]
    assert len(marcados) == len(no_obtenidos)
    assert "Condición de venta — no obtenido" in marcados
    assert "Ítems" not in at.warning[0].value  # [] no es "no obtenido"


def test_sin_ningun_campo_avisa_que_no_se_pudo_leer():
    at, _ = extraer(respuesta(200, VACIA))
    assert at.error[0].value == "No se pudo leer el comprobante. Completá los campos a mano."
    assert all(w.value in ("", None) for w in [*at.text_input, *at.number_input])


def test_descarga_no_disponible_antes_de_confirmar():
    at, _ = extraer(respuesta(200, PARCIAL))
    assert len(at.get("download_button")) == 0


def test_corregir_completar_y_confirmar_habilita_la_descarga():
    at, _ = extraer(respuesta(200, PARCIAL))
    campo(at, "Razón social").input("ACME SA")
    campo(at, "Condición de venta — no obtenido").input("Contado")
    campo(at, "Total").set_value(121.5)
    boton(at, "Confirmar campos").click().run()
    assert at.subheader[0].value == "Descargar JSON"
    assert len(at.get("download_button")) == 1
    validada = at.session_state.validada
    assert validada["razon_social_emisor"] == "ACME SA"
    assert validada["condicion_venta"] == "Contado"
    assert validada["total"] == 121.5
    assert validada["impuestos"] == [{"descripcion_impuesto": "IVA 21%", "importe": 21.0}]
    assert validada["items"] == []
    assert validada["cuit_emisor"] is None


def test_cancelar_vuelve_a_la_carga_sin_json():
    at, _ = extraer(respuesta(200, PARCIAL))
    boton(at, "Cancelar").click().run()
    assert at.subheader[0].value == "Cargar factura"
    assert at.info[0].value == "Proceso cancelado: no se entregó ningún JSON."
    assert "factura" not in at.session_state
    assert "validada" not in at.session_state


@pytest.mark.parametrize(
    ("respuesta_backend", "error"),
    [
        (respuesta(502, {"detail": {"motivo": "fallo_extraccion", "mensaje": "No se pudo completar la extracción."}}), None),
        (None, httpx.ReadTimeout("sin respuesta")),
    ],
    ids=["fallo-claude", "timeout"],
)
def test_fallo_de_extraccion_avisa_y_vuelve_a_la_carga(respuesta_backend, error):
    at, _ = extraer(respuesta_backend, error)
    assert at.subheader[0].value == "Cargar factura"
    assert at.error[0].value == "No se pudo completar la extracción."
    assert "pdf" not in at.session_state


def test_sesion_perdida_durante_la_extraccion_vuelve_al_login():
    at, _ = extraer(respuesta(401, {"detail": "Sesión no iniciada"}))
    assert at.subheader[0].value == "Iniciar sesión"


def test_armar_json_respeta_el_orden_del_esquema():
    valores = dict(reversed(list((PARCIAL | {"condicion_venta": "Contado"}).items())))
    datos = json.loads(armar_json(valores))
    assert list(datos) == list(Factura.model_fields)
    assert datos["condicion_venta"] == "Contado"
