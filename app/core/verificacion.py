class Rechazo(Exception):
    """Motivo por el que no se procesa un archivo, con el mensaje para el usuario (RF-22)."""

    def __init__(self, motivo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.motivo = motivo
        self.mensaje = mensaje


def es_pdf(contenido: bytes) -> bool:
    # La especificación admite el encabezado %PDF- dentro del primer KB
    return b"%PDF-" in contenido[:1024]


def verificar_pdf(contenido: bytes) -> None:
    """Rechaza, antes de llamar a Claude, todo archivo que no se deba procesar."""
    if not es_pdf(contenido):
        raise Rechazo("no_es_pdf", "El archivo no es un PDF.")
