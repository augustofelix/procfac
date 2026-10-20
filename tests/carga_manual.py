"""Carga manual de los JSON esperados del Conjunto de referencia.

    make cargar-json

Herramienta de prueba, no es parte de la app: muestra cada PDF de tests/data/ y guarda
al lado su JSON esperado (mismo nombre, extensión .json) con los datos cargados a mano.
No llama a Claude. La carpeta se puede cambiar con la variable PROCFAC_CARPETA_PDF.
"""

import json
import os
from pathlib import Path

import pdfplumber
import streamlit as st
from pydantic import ValidationError

from app.core.esquema import Factura
from app.core.normalizacion import normalizar
from app.ui.validacion import armar_json, campos

CARPETA = Path(os.environ.get("PROCFAC_CARPETA_PDF", Path(__file__).resolve().parent / "data"))
# Un JSON nuevo arranca sin datos; items e impuestos en [] (sin filas)
NUEVA = {campo: None for campo in Factura.model_fields} | {"items": [], "impuestos": []}


def ruta_json(pdf: Path) -> Path:
    return pdf.with_suffix(".json")


def preparar(valores: dict) -> tuple[dict | None, list[str]]:
    """Lleva los valores a los formatos del Esquema de salida, como la extracción.

    Devuelve los datos a guardar, o None y los errores que impiden guardarlos.
    """
    try:
        factura = normalizar(Factura.model_validate(valores))
    except ValidationError as error:
        return None, [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]
    errores = [
        f"{campo} debe tener 11 dígitos"
        for campo in ("cuit_emisor", "cuit_receptor")
        if getattr(factura, campo) is not None and len(getattr(factura, campo)) != 11
    ]
    if valores["fecha_comprobante"] and factura.fecha_comprobante is None:
        errores.append("fecha_comprobante no es una fecha válida (AAAA-MM-DD o DD/MM/AAAA)")
    return (None, errores) if errores else (factura.model_dump(), [])


def cargar_existente(pdf: Path) -> tuple[dict, str | None]:
    """El JSON ya guardado para editarlo, o uno nuevo; con un aviso si no se pudo leer."""
    if not ruta_json(pdf).exists():
        return NUEVA, None
    try:
        return Factura.model_validate_json(ruta_json(pdf).read_text(encoding="utf-8")).model_dump(), None
    except (ValidationError, ValueError):
        return NUEVA, f"{ruta_json(pdf).name} no cumple el Esquema de salida: se muestra vacío."


@st.cache_data(show_spinner=False)
def _paginas(ruta: str, modificado: float) -> tuple[list, list[str]]:
    with pdfplumber.open(ruta) as pdf:
        return (
            [pagina.to_image(resolution=100).original for pagina in pdf.pages],
            [pagina.extract_text() or "" for pagina in pdf.pages],
        )


def _mostrar_pdf(pdf: Path) -> None:
    try:
        imagenes, textos = _paginas(str(pdf), pdf.stat().st_mtime)
    except Exception as error:
        st.error(f"No se pudo abrir el PDF: {type(error).__name__}")
        return
    with st.expander("Texto extraído (para copiar)"):
        for numero, texto in enumerate(textos, 1):
            st.text_area(f"Página {numero}", texto or "(sin texto)", height=200, key=f"texto_{pdf.name}_{numero}")
    for imagen in imagenes:
        st.image(imagen, width="stretch")


def main() -> None:
    st.set_page_config(page_title="JSON esperados", layout="wide")
    st.title("JSON esperados del Conjunto de referencia")
    pdfs = sorted(p for p in CARPETA.iterdir() if p.suffix.lower() == ".pdf") if CARPETA.is_dir() else []
    if not pdfs:
        st.info(f"No hay PDF en {CARPETA}")
        return
    st.caption(f"{sum(ruta_json(p).exists() for p in pdfs)} de {len(pdfs)} PDF con JSON esperado, en {CARPETA}")
    pdf = st.selectbox(
        "PDF", pdfs, format_func=lambda p: f"{'✔' if ruta_json(p).exists() else '—'}  {p.name}"
    )
    existente, aviso = cargar_existente(pdf)
    if aviso:
        st.warning(aviso)

    izquierda, derecha = st.columns(2)
    with izquierda:
        _mostrar_pdf(pdf)
    with derecha:
        st.caption("Campo vacío = null. Ítems e impuestos sin filas = [].")
        with st.form(f"json_{pdf.name}"):
            valores = campos(existente, pdf.stem, no_obtenidos=[])
            reemplaza = ruta_json(pdf).exists()
            guardar = st.form_submit_button(
                "Guardar JSON (reemplaza el actual)" if reemplaza else "Guardar JSON", type="primary"
            )
        if guardar:
            # Una tabla sin filas guarda [], no null
            valores = valores | {campo: valores[campo] or [] for campo in ("items", "impuestos")}
            datos, errores = preparar(valores)
            if errores:
                st.error("No se guardó:\n\n" + "\n".join(f"- {error}" for error in errores))
            else:
                ruta_json(pdf).write_text(armar_json(datos) + "\n", encoding="utf-8")
                st.success(f"Guardado {ruta_json(pdf).name}")


if __name__ == "__main__":
    main()
