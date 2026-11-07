"""Valoración: reverse DCF, valor justo conservador, precio de entrada, semáforo y tramos.

Replica las reglas de la pestaña Watchlist del Sheet:
- Verde: precio ≤ entrada. Amarillo: entre entrada y valor justo. Rojo: sobre el valor justo.
- Techo 5% de la cartera por posición, tramos 40/30/30.
"""
from __future__ import annotations

from statistics import median


def wacc(tasa_libre: float, beta: float = 1.0, prima_mercado: float = 0.05) -> float:
    """CAPM simple. Para compounders con poca deuda, el costo de capital ≈ costo del patrimonio."""
    return tasa_libre + beta * prima_mercado


def valor_presente(fcf0: float, crec: float, tasa: float, crec_terminal: float = 0.03, anios: int = 10,
                   anios_desvanecimiento: int = 5) -> float:
    """VP de un flujo que crece a `crec` y converge linealmente a `crec_terminal` en los últimos años."""
    if tasa <= crec_terminal:
        raise ValueError("La tasa de descuento debe superar al crecimiento terminal")
    vp, flujo = 0.0, fcf0
    for t in range(1, anios + 1):
        if t <= anios - anios_desvanecimiento:
            g = crec
        else:
            paso = (t - (anios - anios_desvanecimiento)) / anios_desvanecimiento
            g = crec + (crec_terminal - crec) * paso
        flujo *= 1 + g
        vp += flujo / (1 + tasa) ** t
    terminal = flujo * (1 + crec_terminal) / (tasa - crec_terminal)
    return vp + terminal / (1 + tasa) ** anios


def reverse_dcf(valor_empresa: float, fcf0: float, tasa: float, crec_terminal: float = 0.03,
                anios: int = 10) -> float | None:
    """Crecimiento anual de FCF que el precio actual ya descuenta (bisección). None si FCF ≤ 0."""
    if fcf0 is None or fcf0 <= 0 or valor_empresa <= 0:
        return None
    lo, hi = -0.5, 1.5
    for _ in range(100):
        mid = (lo + hi) / 2
        if valor_presente(fcf0, mid, tasa, crec_terminal, anios) < valor_empresa:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def valor_justo_por_accion(fcf0: float, acciones: float, deuda_neta: float, crec: float, tasa: float,
                           crec_terminal: float = 0.03, anios: int = 10) -> float:
    ve = valor_presente(fcf0, crec, tasa, crec_terminal, anios)
    return (ve - deuda_neta) / acciones


def crecimiento_conservador(historicos: list[float | None], recorte: float = 0.25, tope: float = 0.20) -> float | None:
    """Toma el menor de los crecimientos históricos disponibles, le aplica un recorte y un tope."""
    xs = [x for x in historicos if x is not None]
    if not xs:
        return None
    return min(min(xs) * (1 - recorte), tope)


def precio_entrada(valor_justo: float, margen_seguridad: float) -> float:
    return valor_justo * (1 - margen_seguridad)


def semaforo(precio: float, entrada: float, justo: float) -> str:
    if precio <= entrada:
        return "VERDE"
    if precio <= justo:
        return "AMARILLO"
    return "ROJO"


def tramos(valor_cartera: float, techo: float = 0.05, reparto=(0.40, 0.30, 0.30)) -> dict:
    tope = valor_cartera * techo
    return {"techo": round(tope), "tramos": [round(tope * r) for r in reparto]}


def mediana_pe(precios_mensuales: list[tuple[str, float]], eps_anual: dict[str, float], meses: int = 60) -> float | None:
    """Mediana del P/E (con el EPS del último año fiscal ya cerrado) en los últimos `meses`."""
    cierres = sorted(eps_anual)
    pes = []
    for fecha, p in precios_mensuales[-meses:]:
        previos = [c for c in cierres if c <= fecha]
        if not previos:
            continue
        eps = eps_anual[previos[-1]]
        if eps and eps > 0:
            pes.append(p / eps)
    return median(pes) if pes else None
