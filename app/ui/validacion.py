"""Pantalla para que el usuario valide, corrija y complete los campos extraídos."""

import json

import pandas as pd
import streamlit as st

from app.core.esquema import CAMPOS_LISTA, Factura, Impuesto, Item, campos_no_obtenidos, nada_obtenido

ETIQUETAS = {
    "punto_venta": "Punto de venta",
    "numero_comprobante": "Número de comprobante",
    "fecha_comprobante": "Fecha (AAAA-MM-DD)",
    "condicion_venta": "Condición de venta",
    "cuit_emisor": "CUIT",
    "razon_social_emisor": "Razón social",
    "domicilio_emisor": "Domicilio",
    "localidad_emisor": "Localidad",
    "condicion_iva_emisor": "Condición frente al IVA",
    "cuit_receptor": "CUIT",
    "razon_social_receptor": "Razón social",
    "domicilio_receptor": "Domicilio",
    "localidad_receptor": "Localidad",
    "condicion_iva_receptor": "Condición frente al IVA",
    "items": "Ítems",
    "subtotal": "Subtotal",
    "impuestos": "Impuestos",
    "total": "Total",
}

SECCIONES = {
    "Comprobante": ("punto_venta", "numero_comprobante", "fecha_comprobante", "condicion_venta"),
    "Emisor": ("cuit_emisor", "razon_social_emisor", "domicilio_emisor", "localidad_emisor", "condicion_iva_emisor"),
    "Receptor": (
        "cuit_receptor",
        "razon_social_receptor",
        "domicilio_receptor",
        "localidad_receptor",
        "condicion_iva_receptor",
    ),
    "Detalle": ("items",),
    "Totales": ("subtotal", "impuestos", "total"),
}

ENTEROS = {"punto_venta", "numero_comprobante"}
IMPORTES = {"subtotal", "total"}
COLUMNAS = {"items": list(Item.model_fields), "impuestos": list(Impuesto.model_fields)}
COLUMNAS_NUMERICAS = {"cantidad", "precio_unitario", "subtotal_item", "importe"}


def _nombre_completo(campo: str) -> str:
    for seccion, campos in SECCIONES.items():
        if campo in campos and seccion in ("Emisor", "Receptor"):
            return f"{ETIQUETAS[campo]} del {seccion.lower()}"
    return ETIQUETAS[campo]


def _etiqueta(campo: str, no_obtenido: bool) -> str:
    return f"{ETIQUETAS[campo]} — no obtenido" if no_obtenido else ETIQUETAS[campo]


def _campo(campo: str, valor, no_obtenido: bool, clave: str):
    etiqueta = _etiqueta(campo, no_obtenido)
    if campo in ENTEROS:
        return st.number_input(etiqueta, value=valor, step=1, format="%d", key=clave)
    if campo in IMPORTES:
        return st.number_input(etiqueta, value=valor, step=0.01, format="%.2f", key=clave)
    return st.text_input(etiqueta, value=valor or "", key=clave).strip() or None


def _celda(valor):
    if isinstance(valor, str):
        return valor.strip() or None
    if pd.isna(valor):
        return None
    return valor.item() if hasattr(valor, "item") else valor


def _tabla(campo: str, filas: list[dict] | None, no_obtenido: bool, clave: str) -> list[dict] | None:
    st.markdown(f"**{_etiqueta(campo, no_obtenido)}**")
    columnas = COLUMNAS[campo]
    tabla = pd.DataFrame(filas or [], columns=columnas).astype(
        {columna: "float64" for columna in columnas if columna in COLUMNAS_NUMERICAS}
    )
    configuracion = {
        columna: st.column_config.NumberColumn(columna) if columna in COLUMNAS_NUMERICAS else st.column_config.TextColumn(columna)
        for columna in columnas
    }
    editada = st.data_editor(
        tabla, num_rows="dynamic", hide_index=True, column_config=configuracion, key=clave, width="stretch"
    )
    registros = [{columna: _celda(valor) for columna, valor in fila.items()} for fila in editada.to_dict("records")]
    registros = [registro for registro in registros if any(valor is not None for valor in registro.values())]
    # Sin filas: sigue sin obtenerse (null) o el comprobante no tiene ninguna ([])
    if not registros and filas is None:
        return None
    return registros


def campos(factura: dict, sufijo_clave: str, no_obtenidos: list[str]) -> dict:
    """Un widget editable por campo del Esquema de salida; devuelve los valores cargados."""
    valores = {}
    for seccion, campos_seccion in SECCIONES.items():
        st.markdown(f"#### {seccion}")
        for campo in campos_seccion:
            clave = f"{campo}_{sufijo_clave}"
            if campo in CAMPOS_LISTA:
                valores[campo] = _tabla(campo, factura[campo], campo in no_obtenidos, clave)
            else:
                valores[campo] = _campo(campo, factura[campo], campo in no_obtenidos, clave)
    return valores


def formulario(factura: dict, sufijo_clave: str) -> tuple[str, dict | None] | None:
    """Muestra los campos para validar (RF-12, RF-13, RF-16).

    Devuelve ("confirmar", valores) cuando el usuario los valida de forma explícita,
    ("cancelar", None) si cancela, o None mientras no decide.
    """
    modelo = Factura.model_validate(factura)
    no_obtenidos = campos_no_obtenidos(modelo)
    if nada_obtenido(modelo):
        st.error("No se pudo leer el comprobante. Completá los campos a mano.")  # RF-17, AC-13
    elif no_obtenidos:
        # RF-15, AC-11
        st.warning(
            "No se pudieron obtener: " + ", ".join(_nombre_completo(c) for c in no_obtenidos)
            + ". Completalos si corresponde."
        )
    st.caption("Los valores los extrajo una IA y pueden tener errores: revisalos antes de confirmar.")

    with st.form("validacion"):
        valores = campos(factura, sufijo_clave, no_obtenidos)
        confirmar, cancelar = st.columns(2)
        confirmado = confirmar.form_submit_button("Confirmar campos", type="primary")
        cancelado = cancelar.form_submit_button("Cancelar")
    if confirmado:
        return "confirmar", valores
    if cancelado:
        return "cancelar", None
    return None


def armar_json(valores: dict) -> str:
    """El JSON a descargar, con los campos en el orden del Esquema de salida (RF-07).

    Los valores corregidos o completados por el usuario no se validan (fuera del alcance).
    """
    return json.dumps({campo: valores[campo] for campo in Factura.model_fields}, ensure_ascii=False, indent=2)
