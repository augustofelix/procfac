"""PDF sintéticos para los tests, generados en memoria con reportlab."""

import io

from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas


def generar_pdf(*paginas: list[str], contrasena: str | None = None) -> bytes:
    """Un PDF con una página por lista de líneas; una lista vacía es una página sin texto."""
    salida = io.BytesIO()
    cifrado = StandardEncryption(contrasena, ownerPassword="dueño") if contrasena else None
    lienzo = canvas.Canvas(salida, encrypt=cifrado)
    for lineas in paginas:
        for i, linea in enumerate(lineas):
            lienzo.drawString(50, 800 - 15 * i, linea)
        lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def factura(
    copia: str = "ORIGINAL",
    letra: str = "A",
    codigo: str = "01",
    numeracion: str = "Punto de Venta: 00003 Comp. Nro: 00001234",
    titulo: str = "FACTURA",
) -> list[str]:
    """Líneas del encabezado de un comprobante con el formato de AFIP."""
    return [
        copia,
        titulo,
        letra,
        f"COD. {codigo}",
        numeracion,
        "Fecha de Emisión: 01/10/2026",
        "CUIT: 30-12345678-9",
    ]


FACTURA_A = generar_pdf(factura())
