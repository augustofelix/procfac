import io

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect

NO_FACTURA_A = "No se pudo identificar el comprobante como factura A."


class Rechazo(Exception):
    """Motivo por el que no se procesa un archivo, con el mensaje para el usuario (RF-22)."""

    def __init__(self, motivo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.motivo = motivo
        self.mensaje = mensaje


def es_pdf(contenido: bytes) -> bool:
    # La especificación admite el encabezado %PDF- dentro del primer KB
    return b"%PDF-" in contenido[:1024]


def _causado_por(error: BaseException, tipo: type[BaseException]) -> bool:
    while error is not None:
        if isinstance(error, tipo):
            return True
        error = error.__cause__ or error.__context__
    return False


def _textos_por_pagina(contenido: bytes, max_paginas: int) -> list[str]:
    try:
        pdf = pdfplumber.open(io.BytesIO(contenido))
    except Exception as error:
        if _causado_por(error, PDFPasswordIncorrect):
            # Protegido con contraseña: no se puede leer su tipo (AC-18)
            raise Rechazo("no_factura_a", NO_FACTURA_A)
        raise Rechazo("no_es_pdf", "El archivo no es un PDF.")
    with pdf:
        if len(pdf.pages) > max_paginas:
            raise Rechazo("demasiadas_paginas", f"El PDF supera las {max_paginas} páginas.")
        return [pagina.extract_text() or "" for pagina in pdf.pages]


def verificar_pdf(contenido: bytes, max_paginas: int) -> None:
    """Rechaza, antes de llamar a Claude, todo archivo que no se deba procesar."""
    if not es_pdf(contenido):
        raise Rechazo("no_es_pdf", "El archivo no es un PDF.")
    textos = _textos_por_pagina(contenido, max_paginas)  # RF-28, AC-33
    if not any(texto.strip() for texto in textos):
        # Sin texto extraíble: PDF escaneado, fuera de alcance (AC-18)
        raise Rechazo("no_factura_a", NO_FACTURA_A)
