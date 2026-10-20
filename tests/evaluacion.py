"""Evalúa la extracción contra el Conjunto de referencia (RNF-02, RNF-03, RNF-04).

Llama a la API real de Claude (tiene costo). Cada PDF de tests/data/ con su JSON
esperado al lado (mismo nombre, extensión .json) es una factura del conjunto.

    uv run python -m tests.evaluacion                  # precisión y p95 (AC-01, AC-15, AC-16, AC-20, AC-21, AC-27, AC-31)
    uv run python -m tests.evaluacion --simultaneas 5  # 5 extracciones a la vez (AC-29)

Solo informa nombres de campos y porcentajes, nunca valores de las facturas.
"""

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from pathlib import Path

from app.api.extraer import obtener_extractor
from app.api.verificar import MAX_PAGINAS
from app.core.esquema import Factura
from app.core.extraccion import FalloExtraccion
from app.core.verificacion import Rechazo, verificar_pdf

CARPETA = Path(__file__).resolve().parent / "data"
PRECISION_MINIMA = 0.90
TIEMPO_MAXIMO = 30.0

CAMPOS_ESCALARES = [campo for campo in Factura.model_fields if campo not in ("items", "impuestos")]
CAMPOS_ITEM = ["codigo", "descripcion", "precio_unitario", "subtotal_item"]
METRICAS = [*CAMPOS_ESCALARES, "impuestos", "cantidad_de_items", "cantidad_de_cada_item"] + [
    f"items.{campo}" for campo in CAMPOS_ITEM
]


def _mismos_pares(obtenidos: list[dict] | None, esperados: list[dict] | None) -> bool:
    """Los mismos pares descripcion_impuesto e importe, sin importar el orden."""
    if obtenidos is None or esperados is None:
        return obtenidos is esperados

    def pares(impuestos):
        return Counter((i["descripcion_impuesto"], i["importe"]) for i in impuestos)

    return pares(obtenidos) == pares(esperados)


def _mismo_campo_en_todos_los_items(obtenidos, esperados, campo: str) -> bool:
    """Ítems comparados por posición; con otra cantidad de ítems la factura es incorrecta."""
    if obtenidos is None or esperados is None:
        return obtenidos is esperados
    if len(obtenidos) != len(esperados):
        return False
    return all(o[campo] == e[campo] for o, e in zip(obtenidos, esperados))


def comparar(obtenida: dict | None, esperada: dict) -> dict[str, bool]:
    """Qué métricas de RNF-03 acierta una factura; si la extracción falló, ninguna."""
    if obtenida is None:
        return dict.fromkeys(METRICAS, False)
    aciertos = {campo: obtenida[campo] == esperada[campo] for campo in CAMPOS_ESCALARES}
    aciertos["impuestos"] = _mismos_pares(obtenida["impuestos"], esperada["impuestos"])
    items, items_esperados = obtenida["items"], esperada["items"]
    aciertos["cantidad_de_items"] = (
        items is items_esperados if items is None or items_esperados is None else len(items) == len(items_esperados)
    )
    aciertos["cantidad_de_cada_item"] = _mismo_campo_en_todos_los_items(items, items_esperados, "cantidad")
    for campo in CAMPOS_ITEM:
        aciertos[f"items.{campo}"] = _mismo_campo_en_todos_los_items(items, items_esperados, campo)
    return aciertos


def percentil_95(tiempos: list[float]) -> float:
    """Percentil 95 por rango más cercano."""
    ordenados = sorted(tiempos)
    return ordenados[math.ceil(0.95 * len(ordenados)) - 1]


async def _extraer_midiendo(extractor, contenido: bytes) -> tuple[dict | None, float, str | None]:
    inicio = time.perf_counter()
    try:
        factura = await extractor.extraer(contenido)
        return factura.model_dump(), time.perf_counter() - inicio, None
    except FalloExtraccion as fallo:
        return None, time.perf_counter() - inicio, str(fallo)


def _conjunto() -> list[tuple[Path, dict]]:
    pdfs = sorted(p for p in CARPETA.iterdir() if p.suffix.lower() == ".pdf")
    return [(pdf, json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))) for pdf in pdfs if pdf.with_suffix(".json").exists()]


async def evaluar(detalle: bool) -> None:
    conjunto = _conjunto()
    if not conjunto:
        raise SystemExit(f"No hay PDF con su JSON esperado en {CARPETA}")
    extractor = obtener_extractor()
    resultados, tiempos, validas = [], [], 0
    for pdf, esperada in conjunto:
        contenido = pdf.read_bytes()
        try:
            verificar_pdf(contenido, MAX_PAGINAS)
        except Rechazo as rechazo:
            print(f"RECHAZADA  {pdf.name}: {rechazo.mensaje}")
            resultados.append(comparar(None, esperada))
            continue
        obtenida, segundos, fallo = await _extraer_midiendo(extractor, contenido)
        tiempos.append(segundos)
        validas += fallo is None
        aciertos = comparar(obtenida, esperada)
        resultados.append(aciertos)
        estado = f"FALLÓ ({fallo})" if fallo else f"{sum(aciertos.values())}/{len(aciertos)} métricas"
        print(f"{segundos:5.1f} s  {pdf.name}: {estado}")
        if detalle and not fallo:
            errores = [metrica for metrica, ok in aciertos.items() if not ok]
            if errores:
                print("         no coinciden: " + ", ".join(errores))

    total = len(resultados)
    # Una respuesta que llega sin fallo ya pasó la validación del Esquema de salida
    print(f"\nFacturas: {total}  (AC-01: {validas}/{total} con respuesta que cumple el esquema)")
    print(f"\n{'Métrica (RNF-03)':32} {'Precisión':>9}  >= 90%")
    for metrica in METRICAS:
        precision = sum(r[metrica] for r in resultados) / total
        print(f"{metrica:32} {precision:9.1%}  {'sí' if precision >= PRECISION_MINIMA else 'NO'}")
    if tiempos:
        p95 = percentil_95(tiempos)
        print(f"\nTiempo p95 (AC-27): {p95:.1f} s  {'sí' if p95 < TIEMPO_MAXIMO else 'NO'} < {TIEMPO_MAXIMO:g} s")


def _aceptado(pdf: Path) -> bool:
    try:
        verificar_pdf(pdf.read_bytes(), MAX_PAGINAS)
    except Rechazo:
        return False
    return True


async def evaluar_simultaneas(cantidad: int) -> None:
    # Solo PDF que pasan los filtros previos: nada fuera de alcance llega a Claude
    conjunto = [(pdf, esperada) for pdf, esperada in _conjunto() if _aceptado(pdf)][:cantidad]
    if len(conjunto) < cantidad:
        raise SystemExit(f"Se necesitan {cantidad} PDF con su JSON esperado en {CARPETA}")
    extractor = obtener_extractor()
    resultados = await asyncio.gather(*(_extraer_midiendo(extractor, pdf.read_bytes()) for pdf, _ in conjunto))
    for (pdf, _), (_, segundos, fallo) in zip(conjunto, resultados):
        print(f"{segundos:5.1f} s  {'sí' if segundos < TIEMPO_MAXIMO and not fallo else 'NO'}  {pdf.name}{f' FALLÓ ({fallo})' if fallo else ''}")


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--simultaneas", type=int, help="extrae N facturas a la vez y mide cada tiempo (AC-29)")
    argumentos.add_argument("--detalle", action="store_true", help="lista las métricas que no coinciden por factura")
    opciones = argumentos.parse_args()
    if opciones.simultaneas:
        asyncio.run(evaluar_simultaneas(opciones.simultaneas))
    else:
        asyncio.run(evaluar(opciones.detalle))


if __name__ == "__main__":
    main()
