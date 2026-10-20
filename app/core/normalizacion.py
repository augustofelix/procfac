"""Lleva lo que devuelve Claude a los formatos del Esquema de salida."""

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.core.esquema import Factura, FacturaExtraida, Impuesto, Item

_FORMATOS_FECHA = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")


def _texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


def _cuit(valor: str | None) -> str | None:
    """Solo los dígitos: 30-12345678-9 pasa a 30123456789."""
    if valor is None:
        return None
    return re.sub(r"\D", "", valor) or None


def _fecha(valor: str | None) -> str | None:
    """AAAA-MM-DD; una fecha que no se puede interpretar queda como no obtenida."""
    valor = _texto(valor)
    if valor is None:
        return None
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        pass
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue
    return None


def _importe(valor: float | None) -> float | None:
    """2 decimales, mitad hacia arriba sobre el número tal como se escribió (100.005 -> 100.01)."""
    if valor is None:
        return None
    return float(Decimal(repr(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def normalizar(factura: Factura | FacturaExtraida) -> Factura:
    """La factura en el Esquema de salida; un texto vacío pasa a null."""
    datos = {
        campo: _texto(valor) if isinstance(valor, str) else valor
        for campo, valor in factura
        if campo not in ("impuestos", "items")
    }
    datos["cuit_emisor"] = _cuit(factura.cuit_emisor)
    datos["cuit_receptor"] = _cuit(factura.cuit_receptor)
    datos["fecha_comprobante"] = _fecha(factura.fecha_comprobante)
    datos["subtotal"] = _importe(factura.subtotal)
    datos["total"] = _importe(factura.total)
    datos["impuestos"] = None if factura.impuestos is None else [
        Impuesto(descripcion_impuesto=_texto(i.descripcion_impuesto), importe=_importe(i.importe))
        for i in factura.impuestos
    ]
    datos["items"] = None if factura.items is None else [
        Item(
            codigo=_texto(i.codigo),
            descripcion=_texto(i.descripcion),
            cantidad=i.cantidad,  # sin redondeo
            precio_unitario=_importe(i.precio_unitario),
            subtotal_item=_importe(i.subtotal_item),
        )
        for i in factura.items
    ]
    return Factura(**datos)
