import io
import re
import unicodedata

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect

NO_FACTURA_A = "No se pudo identificar el comprobante como factura A."

# Código AFIP del tipo de comprobante: 01 es factura A; 51 factura M, 201 FCE MiPyME A,
# 02/03 notas de débito/crédito A, 06 factura B, 11 factura C, 19 factura E, etc.
CODIGO_FACTURA_A = 1
# "COD. 01", "Cod. 1", "Código N° 01", "Código Nro001" o "01 FACTURA" al comienzo de una línea
_CODIGO = (
    re.compile(r"\bC[OÓ]D(?:IGO)?\.?\s*(?:N(?:RO|°|º|O)?\.?\s*)?:?\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"^\s*(\d{2,3})\s+FACTURA\b", re.IGNORECASE | re.MULTILINE),
)
# Sin código, la letra del comprobante sola en una línea
_LETRA_A = re.compile(r"^\s*A\s*$", re.MULTILINE)
# Sin código, estas menciones indican un comprobante fuera de alcance (texto sin tildes)
_FUERA_DE_ALCANCE = (
    "NOTA DE CREDITO",
    "NOTA DE DEBITO",
    "RECIBO",
    "REMITO",
    "LIQUIDACION",
    "MIPYME",
    "CREDITO ELECTRONICA",
)

# Punto de venta y número: "Punto de Venta: 00003 Comp. Nro: 00001234" o "N° 0003-00001234"
_NUMERACION = (
    re.compile(
        r"Punto\s+de\s+Venta\s*:?\s*(\d{1,5}).{0,40}?Comp(?:robante)?\.?\s*N(?:ro|°|º)?\.?\s*:?\s*(\d{1,8})",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"(?<!\d)(\d{4,5})\s*-\s*(\d{8})(?!\d)"),
)


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


def codigo_comprobante(texto: str) -> int | None:
    """Primer código de tipo de comprobante de la página."""
    for patron in _CODIGO:
        coincidencia = patron.search(texto)
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def numeracion(texto: str) -> tuple[int, int] | None:
    """Punto de venta y número del comprobante de la página, sin ceros a la izquierda."""
    for patron in _NUMERACION:
        coincidencia = patron.search(texto)
        if coincidencia:
            return int(coincidencia.group(1)), int(coincidencia.group(2))
    return None


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()


def es_factura_a(textos: list[str]) -> bool:
    """Todas las páginas con código tienen 01; sin código, alcanza con la letra A (RF-24)."""
    texto = _sin_tildes("\n".join(textos))
    if "FACTURA" not in texto:
        return False
    codigos = {codigo_comprobante(pagina) for pagina in textos} - {None}
    if codigos:
        return codigos == {CODIGO_FACTURA_A}
    return bool(_LETRA_A.search(texto)) and not any(palabra in texto for palabra in _FUERA_DE_ALCANCE)


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
    # Las copias ORIGINAL, DUPLICADO y TRIPLICADO repiten la numeración: una sola factura
    if len({numeracion(texto) for texto in textos} - {None}) > 1:
        raise Rechazo("mas_de_una_factura", "El PDF contiene más de una factura.")  # RF-18, AC-14
    if not es_factura_a(textos):
        raise Rechazo("no_factura_a", NO_FACTURA_A)
