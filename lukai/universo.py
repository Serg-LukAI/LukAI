"""Construcción del universo del screener (ver config/universo.yaml)."""
from __future__ import annotations

import re

import yaml

from . import edgar, red


def cargar_config() -> dict:
    return yaml.safe_load((red.RAIZ / "config" / "universo.yaml").read_text())


def ideas() -> list[str]:
    txt = (red.RAIZ / "ideas.md").read_text()
    return re.findall(r"^-\s*([A-Z][A-Z0-9.\-]{0,9})\s+—", txt, flags=re.M)


def construir() -> list[dict]:
    """Lista de {ticker, cik, nombre, origen}. Sin duplicados (una entrada por CIK)."""
    cfg = cargar_config()
    tickers = edgar.mapa_tickers()
    por_cik: dict[int, list[str]] = {}
    for t, info in tickers.items():
        if info["bolsa"] in cfg["bolsas_permitidas"]:
            por_cik.setdefault(info["cik"], []).append(t)

    salida: dict[int, dict] = {}
    for cik, f in edgar.float_publico(cfg["periodos_float"]).items():
        if f["float"] >= cfg["min_float_usd"] and cik in por_cik:
            # Varias clases (GOOGL/GOOG): se toma el ticker más corto/alfabético como representante.
            clases = sorted(por_cik[cik], key=lambda x: (len(x), x))
            salida[cik] = {"ticker": clases[0], "clases": clases, "cik": cik, "nombre": f["nombre"],
                           "origen": "float ≥ mínimo", "float_usd": f["float"]}

    for origen, lista in (("extranjero curado", cfg.get("extranjeros", [])), ("idea manual", ideas())):
        for t in lista:
            info = tickers.get(t.upper())
            if not info:
                continue
            salida.setdefault(info["cik"], {"ticker": t.upper(), "cik": info["cik"], "nombre": info["nombre"],
                                            "origen": origen})
            if origen == "idea manual":
                salida[info["cik"]]["idea"] = True
    return sorted(salida.values(), key=lambda x: x["ticker"])


def excluido_por_sic(sic: str | None) -> bool:
    if not sic or not str(sic).isdigit():
        return False
    s = int(sic)
    return any(a <= s <= b for a, b in cargar_config()["excluir_sic"])
