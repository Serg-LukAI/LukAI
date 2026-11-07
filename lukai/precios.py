"""Precios con rutas alternas: Alpha Vantage → Stooq → Yahoo (este último no oficial, marcado como tal).

Los precios solo se piden para finalistas y para la watchlist, nunca para todo el universo:
el screener filtra primero por calidad con datos de EDGAR, que no gasta cupo.
"""
from __future__ import annotations

import csv
import io
import os
from datetime import date

from . import red

AV_KEY = os.environ.get("ALPHAVANTAGE_API_KEY")
STOOQ_KEY = os.environ.get("LUKAI_STOOQ_KEY")


class SinDato(RuntimeError):
    pass


def _alpha_vantage(funcion: str, ttl: float, **params) -> dict:
    if not AV_KEY:
        raise SinDato("Alpha Vantage sin clave (define ALPHAVANTAGE_API_KEY o usa el conector MCP)")
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://www.alphavantage.co/query?function={funcion}&{qs}&apikey={AV_KEY}"
    d = red.obtener_json(url, ttl, clave_cache=f"av:{funcion}:{qs}")
    if not d or "Note" in d or "Information" in d or "Error Message" in d:
        raise SinDato(f"Alpha Vantage {funcion}: {d.get('Note') or d.get('Information') or d.get('Error Message')}")
    return d


def _precio_av(t: str) -> dict:
    q = _alpha_vantage("GLOBAL_QUOTE", 20, symbol=t)["Global Quote"]
    return {"precio": float(q["05. price"]), "fecha": q["07. latest trading day"], "fuente": "Alpha Vantage"}


def _precio_stooq(t: str) -> dict:
    sufijo = f"&apikey={STOOQ_KEY}" if STOOQ_KEY else ""
    url = f"https://stooq.com/q/l/?s={t.lower()}.us&f=sd2t2ohlcv&h&e=csv{sufijo}"
    filas = list(csv.DictReader(io.StringIO(red.obtener(url, 20, clave_cache=f"stooq:{t}"))))
    if not filas or filas[0].get("Close") in (None, "N/D"):
        raise SinDato("Stooq sin dato")
    return {"precio": float(filas[0]["Close"]), "fecha": filas[0]["Date"], "fuente": "Stooq"}


def _precio_yahoo(t: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5d&interval=1d"
    m = red.obtener_json(url, 20)["chart"]["result"][0]["meta"]
    return {"precio": float(m["regularMarketPrice"]), "fecha": date.fromtimestamp(m["regularMarketTime"]).isoformat(),
            "fuente": "Yahoo (no oficial)"}


RUTAS = [("Alpha Vantage", _precio_av), ("Stooq", _precio_stooq), ("Yahoo", _precio_yahoo)]


def precio(ticker: str) -> dict:
    """Primer precio disponible según la ruta de fuentes. `verificado` es False si solo respondió Yahoo."""
    errores = []
    for nombre, f in RUTAS:
        try:
            r = f(ticker)
        except Exception as e:  # noqa: BLE001 - cualquier falla pasa a la siguiente ruta
            errores.append(f"{nombre}: {e}")
            continue
        r["verificado"] = nombre != "Yahoo"
        if not r["verificado"]:
            r["aviso"] = "Precio solo de fuente no oficial: confírmalo en IBKR antes de usarlo."
        r["errores_previos"] = errores
        return r
    raise SinDato(f"Sin precio para {ticker}. " + " | ".join(errores))


def historico_mensual(ticker: str) -> tuple[list[tuple[str, float]], str]:
    """Cierres mensuales (~5 años) para la mediana histórica del P/E. Devuelve (serie, fuente)."""
    errores = []
    try:
        d = _alpha_vantage("TIME_SERIES_MONTHLY_ADJUSTED", 24, symbol=ticker)["Monthly Adjusted Time Series"]
        return sorted((k, float(v["5. adjusted close"])) for k, v in d.items()), "Alpha Vantage"
    except Exception as e:  # noqa: BLE001
        errores.append(f"Alpha Vantage: {e}")
    try:
        sufijo = f"&apikey={STOOQ_KEY}" if STOOQ_KEY else ""
        txt = red.obtener(f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=m{sufijo}", 24,
                          clave_cache=f"stooq-m:{ticker}")
        filas = list(csv.DictReader(io.StringIO(txt)))
        if filas and "Close" in filas[0]:
            return [(f["Date"], float(f["Close"])) for f in filas], "Stooq"
    except Exception as e:  # noqa: BLE001
        errores.append(f"Stooq: {e}")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=6y&interval=1mo"
        res = red.obtener_json(url, 24)["chart"]["result"][0]
        cierres = res["indicators"]["adjclose"][0]["adjclose"]
        serie = [(date.fromtimestamp(ts).isoformat(), c) for ts, c in zip(res["timestamp"], cierres) if c]
        return serie, "Yahoo (no oficial)"
    except Exception as e:  # noqa: BLE001
        errores.append(f"Yahoo: {e}")
    raise SinDato(f"Sin histórico para {ticker}. " + " | ".join(errores))


def fundamentales_av(ticker: str) -> dict:
    """Ingresos y EPS anuales de Alpha Vantage para la verificación cruzada con EDGAR (2 llamadas, caché 30 días)."""
    inc = _alpha_vantage("INCOME_STATEMENT", 24 * 30, symbol=ticker)["annualReports"]
    ern = _alpha_vantage("EARNINGS", 24 * 30, symbol=ticker)["annualEarnings"]
    return {
        "ingresos": {r["fiscalDateEnding"]: float(r["totalRevenue"]) for r in inc if r["totalRevenue"] != "None"},
        "eps": {r["fiscalDateEnding"]: float(r["reportedEPS"]) for r in ern if r["reportedEPS"] != "None"},
    }
