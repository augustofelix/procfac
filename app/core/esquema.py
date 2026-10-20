"""Esquema de salida de PRD.md (RF-25).

Todos los campos son obligatorios en el JSON pero admiten null: un campo que no se pudo
obtener del comprobante vale null; items e impuestos valen [] si el comprobante no tiene
ninguno. Los decimales se representan como números JSON.
"""

from pydantic import BaseModel, ConfigDict


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Impuesto(_Estricto):
    descripcion_impuesto: str | None
    importe: float | None


class Item(_Estricto):
    codigo: str | None
    descripcion: str | None
    cantidad: float | None
    precio_unitario: float | None
    subtotal_item: float | None


class Factura(_Estricto):
    punto_venta: int | None
    numero_comprobante: int | None
    cuit_emisor: str | None
    razon_social_emisor: str | None
    domicilio_emisor: str | None
    localidad_emisor: str | None
    condicion_iva_emisor: str | None
    cuit_receptor: str | None
    razon_social_receptor: str | None
    domicilio_receptor: str | None
    localidad_receptor: str | None
    condicion_iva_receptor: str | None
    fecha_comprobante: str | None
    condicion_venta: str | None
    subtotal: float | None
    impuestos: list[Impuesto] | None
    total: float | None
    items: list[Item] | None


# Lo que se le pide a Claude. La salida estructurada admite hasta 16 campos con null
# (uniones): los textos se piden como cadena, "" si no figuran, y normalizar() los
# pasa a null. Números, items e impuestos sí admiten null.


class ImpuestoExtraido(_Estricto):
    descripcion_impuesto: str
    importe: float | None


class ItemExtraido(_Estricto):
    codigo: str
    descripcion: str
    cantidad: float | None
    precio_unitario: float | None
    subtotal_item: float | None


class FacturaExtraida(_Estricto):
    punto_venta: int | None
    numero_comprobante: int | None
    cuit_emisor: str
    razon_social_emisor: str
    domicilio_emisor: str
    localidad_emisor: str
    condicion_iva_emisor: str
    cuit_receptor: str
    razon_social_receptor: str
    domicilio_receptor: str
    localidad_receptor: str
    condicion_iva_receptor: str
    fecha_comprobante: str
    condicion_venta: str
    subtotal: float | None
    impuestos: list[ImpuestoExtraido] | None
    total: float | None
    items: list[ItemExtraido] | None


CAMPOS_LISTA = ("impuestos", "items")


def campos_no_obtenidos(factura: Factura) -> list[str]:
    """Campos en null; una lista vacía no cuenta como no obtenida (RF-15, AC-11)."""
    return [campo for campo, valor in factura if valor is None]


def nada_obtenido(factura: Factura) -> bool:
    """Todo en null, salvo items e impuestos que pueden ser null o [] (RF-17, AC-13)."""
    return all(not valor if campo in CAMPOS_LISTA else valor is None for campo, valor in factura)
