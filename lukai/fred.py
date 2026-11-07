"""FRED (Reserva Federal de St. Louis): tasa libre de riesgo y nivel del S&P 500. Oficial, sin clave."""
from __future__ import annotations

import csv
import io

from . import red


def serie(id_serie: str) -> list[tuple[str, float]]:
    txt = red.obtener(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={id_serie}", ttl_horas=12)
    filas = csv.reader(io.StringIO(txt))
    next(filas)
    return [(f, float(v)) for f, v in filas if v not in (".", "")]


def ultimo(id_serie: str) -> dict:
    f, v = serie(id_serie)[-1]
    return {"serie": id_serie, "fecha": f, "valor": v, "fuente": f"FRED {id_serie}"}


def tasa_libre_riesgo() -> dict:
    """Bono del Tesoro a 10 años (DGS10), en decimal."""
    r = ultimo("DGS10")
    r["valor"] = r["valor"] / 100
    return r


def sp500() -> dict:
    """Nivel de precio del S&P 500 (SP500). Es índice de precio, no Total Return: se anota en la nota del mes."""
    return ultimo("SP500")
