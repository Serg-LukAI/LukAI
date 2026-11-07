"""Ratios, knockouts y puntaje del screener. Cálculo determinista: el LLM nunca hace esta aritmética.

Todas las métricas son ratios (márgenes, ROIC, CAGR, apalancamiento), así que no dependen de la moneda:
sirven igual para un 10-K en USD que para un 20-F en EUR o TWD.
"""
from __future__ import annotations

from statistics import median


def _v(serie: dict, c: str):
    x = serie.get(c)
    return None if x is None else x["valor"]


def _div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def cagr(inicio, fin, anios):
    if inicio is None or fin is None or anios <= 0 or inicio <= 0 or fin <= 0:
        return None
    return (fin / inicio) ** (1 / anios) - 1


RATIOS_SPLIT = (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50)


def factores_split(acciones: list[float | None]) -> list[float]:
    """Factor acumulado para expresar cada año en acciones de HOY (EPS ÷ factor, acciones × factor).

    EDGAR conserva el EPS tal como se reportó; los años anteriores a un split quedan sin ajustar.
    Un salto del número de acciones cercano (±15%) a un ratio típico entre dos años seguidos se trata como split.
    """
    n = len(acciones)
    factores = [1.0] * n
    acumulado = 1.0
    for i in range(n - 1, 0, -1):
        a, b = acciones[i - 1], acciones[i]
        if a and b:
            r = b / a
            for s in RATIOS_SPLIT:
                if abs(r / s - 1) <= 0.15:
                    acumulado *= s
                    break
                if abs(r * s - 1) <= 0.15:  # split inverso
                    acumulado /= s
                    break
        factores[i - 1] = acumulado
    return factores


def anuales(series: dict, tasa_impuesto_defecto: float = 0.21) -> list[dict]:
    """Una fila por año fiscal con los rubros base y los ratios derivados."""
    c = series["conceptos"]
    filas = []
    for cierre in series["cierres"]:
        g = lambda k: _v(c[k], cierre)  # noqa: E731
        ingresos = g("ingresos")
        bruta = g("utilidad_bruta")
        if bruta is None and ingresos is not None and g("costo_ventas") is not None:
            bruta = ingresos - g("costo_ventas")
        ebit = g("utilidad_operativa")
        uai, imp = g("utilidad_antes_impuestos"), g("impuestos")
        tasa = _div(imp, uai)
        if tasa is None or not 0 <= tasa <= 0.40:
            tasa = tasa_impuesto_defecto
        deuda = g("deuda_total_lp")
        if deuda is None:
            partes = [g("deuda_lp_no_corriente"), g("deuda_lp_corriente")]
            deuda = sum(p for p in partes if p is not None) if any(p is not None for p in partes) else None
        if deuda is not None and g("deuda_cp") is not None:
            deuda += g("deuda_cp")
        # Conservador: si la empresa no reporta deuda financiera, se asume 0 solo si sí reporta patrimonio.
        if deuda is None and g("patrimonio") is not None:
            deuda = 0.0
        caja = (g("caja") or 0) + (g("inversiones_cp") or 0)
        patrimonio = g("patrimonio")
        arrend = g("arrendamientos")
        if arrend is None and (g("arrendamientos_no_corriente") is not None or g("arrendamientos_corriente") is not None):
            arrend = (g("arrendamientos_no_corriente") or 0) + (g("arrendamientos_corriente") or 0)
        # Capital invertido = deuda financiera + patrimonio − caja + arrendamientos operativos (definición de la skill).
        capital_invertido = (None if patrimonio is None or deuda is None
                             else patrimonio + deuda - caja + (arrend or 0))
        fcf = None
        if g("flujo_operativo") is not None:
            fcf = g("flujo_operativo") - abs(g("capex") or 0)
        ebitda = None if ebit is None else ebit + (g("dya") or 0)
        deuda_neta = None if deuda is None else deuda - caja
        filas.append({
            "cierre": cierre,
            "ingresos": ingresos, "utilidad_bruta": bruta, "ebit": ebit, "utilidad_neta": g("utilidad_neta"),
            "eps": g("eps_diluido"), "fcf": fcf, "ebitda": ebitda, "deuda": deuda, "caja": caja,
            "deuda_neta": deuda_neta, "patrimonio": patrimonio, "activos": g("activos"),
            "arrendamientos": arrend, "dya": g("dya"), "flujo_operativo": g("flujo_operativo"),
            "capex": None if g("capex") is None else abs(g("capex")), "tasa_impuesto": tasa,
            "acciones": g("acciones_diluidas"),
            "margen_bruto": _div(bruta, ingresos), "margen_operativo": _div(ebit, ingresos),
            "margen_fcf": _div(fcf, ingresos),
            "nopat": None if ebit is None else ebit * (1 - tasa),
            "capital_invertido": capital_invertido,
            "deuda_neta_ebitda": _div(deuda_neta, ebitda) if ebitda and ebitda > 0 else None,
            "roe": _div(g("utilidad_neta"), patrimonio) if patrimonio and patrimonio > 0 else None,
            "roa": _div(g("utilidad_neta"), g("activos")),
        })
    for f, fac in zip(filas, factores_split([f["acciones"] for f in filas])):
        if fac != 1.0:
            f["ajuste_split"] = fac
            if f["eps"] is not None:
                f["eps"] /= fac
            if f["acciones"] is not None:
                f["acciones"] *= fac
    # ROIC sobre capital invertido promedio (inicio + fin del año).
    for i, f in enumerate(filas):
        ci = [f["capital_invertido"]] + ([filas[i - 1]["capital_invertido"]] if i else [])
        ci = [x for x in ci if x is not None]
        prom = sum(ci) / len(ci) if ci else None
        f["roic"] = _div(f["nopat"], prom) if prom and prom > 0 else None
    return filas


def resumen(filas: list[dict]) -> dict:
    """Agregados multi-año que usan el screener y la rúbrica."""
    if not filas:
        return {}
    n = len(filas) - 1
    def col(k):  # noqa: E306
        return [f[k] for f in filas if f[k] is not None]
    ult = filas[-1]
    roics = col("roic")
    mo = [f["margen_operativo"] for f in filas]
    # Tendencia: años consecutivos (al final de la serie) en que el margen operativo cayó.
    caidas = 0
    for a, b in zip(mo[::-1][1:], mo[::-1]):
        if a is None or b is None or b >= a:
            break
        caidas += 1
    ini3 = filas[-4] if len(filas) >= 4 else filas[0]
    anios3 = len(filas) - 1 if len(filas) < 4 else 3
    # Algunas empresas (p. ej. Visa, con varias clases de acciones) solo reportan EPS por clase, que no
    # aparece en companyfacts. Si no hay EPS en ningún año, el crecimiento por acción se aproxima con la
    # utilidad neta y se deja constancia.
    eps_disponible = any(f["eps"] is not None for f in filas)
    campo_eps = "eps" if eps_disponible else "utilidad_neta"
    return {
        "eps_fuente": "EPS diluido" if eps_disponible else "utilidad neta (EPS no reportado sin dimensiones)",
        "anios": len(filas),
        "ultimo_cierre": ult["cierre"],
        "cagr_ingresos": cagr(filas[0]["ingresos"], ult["ingresos"], n),
        "cagr_ingresos_3a": cagr(ini3["ingresos"], ult["ingresos"], anios3),
        "cagr_eps": cagr(filas[0][campo_eps], ult[campo_eps], n),
        "cagr_eps_3a": cagr(ini3[campo_eps], ult[campo_eps], anios3),
        "roic_mediana": median(roics) if roics else None,
        "roic_ultimo": ult["roic"],
        "roic_minimo": min(roics) if roics else None,
        "margen_bruto_ultimo": ult["margen_bruto"],
        "margen_bruto_cambio": (None if ult["margen_bruto"] is None or filas[0]["margen_bruto"] is None
                                else ult["margen_bruto"] - filas[0]["margen_bruto"]),
        "margen_operativo_ultimo": ult["margen_operativo"],
        "margen_operativo_cambio": (None if ult["margen_operativo"] is None or filas[0]["margen_operativo"] is None
                                    else ult["margen_operativo"] - filas[0]["margen_operativo"]),
        "anios_caida_margen_operativo": caidas,
        "anios_fcf_positivo": sum(1 for f in filas if f["fcf"] is not None and f["fcf"] > 0),
        "anios_con_fcf": sum(1 for f in filas if f["fcf"] is not None),
        "deuda_neta_ebitda": ult["deuda_neta_ebitda"],
        "caja_neta": ult["deuda_neta"] is not None and ult["deuda_neta"] < 0,
        "roe_ultimo": ult["roe"], "roa_ultimo": ult["roa"],
        "roe_cambio": (None if ult["roe"] is None or filas[0]["roe"] is None else ult["roe"] - filas[0]["roe"]),
        "roa_cambio": (None if ult["roa"] is None or filas[0]["roa"] is None else ult["roa"] - filas[0]["roa"]),
    }


def knockouts(r: dict, k: dict) -> list[str]:
    """Filtros innegociables de la rúbrica (Parte 0) que se pueden verificar con números.

    Las banderas contables y el moat de commodity son cualitativos: quedan para el equity-analyst.
    """
    fallas = []
    if r.get("anios", 0) < k["anios_minimos"]:
        fallas.append(f"Historia insuficiente ({r.get('anios', 0)} años < {k['anios_minimos']})")
        return fallas
    if r["cagr_ingresos_3a"] is not None and r["cagr_ingresos_3a"] < k["cagr_ingresos_3a_min"]:
        fallas.append(f"Ingresos en caída (CAGR 3a {r['cagr_ingresos_3a']:.1%})")
    if r["cagr_eps_3a"] is not None and r["cagr_eps_3a"] < k["cagr_eps_3a_min"]:
        fallas.append(f"EPS en caída (CAGR 3a {r['cagr_eps_3a']:.1%})")
    if r["cagr_eps_3a"] is None and r["cagr_ingresos_3a"] is not None:
        # EPS negativo al inicio o al final: no hay crecimiento medible.
        fallas.append("EPS negativo o no comparable en los últimos 3 años")
    if r["anios_caida_margen_operativo"] >= k["anios_caida_margen_max"]:
        fallas.append(f"Margen operativo cae {r['anios_caida_margen_operativo']} años seguidos")
    if r["roic_mediana"] is None:
        fallas.append("ROIC no calculable (faltan datos de capital)")
    elif r["roic_mediana"] < k["wacc_proxy"]:
        fallas.append(f"ROIC mediano {r['roic_mediana']:.1%} < WACC aprox. {k['wacc_proxy']:.0%}")
    if r["deuda_neta_ebitda"] is not None and r["deuda_neta_ebitda"] > k["deuda_neta_ebitda_max"]:
        fallas.append(f"Deuda neta/EBITDA {r['deuda_neta_ebitda']:.1f}x > {k['deuda_neta_ebitda_max']}x")
    return fallas


def _tramo(valor, ideal, aceptable, puntos):
    if valor is None:
        return 0
    if valor >= ideal:
        return puntos
    if valor >= aceptable:
        return puntos / 2
    return 0


def puntaje_calidad(r: dict, p: dict) -> dict:
    """Puntaje 0-100 de CALIDAD para ordenar candidatos. No es el veredicto: ese sale de la rúbrica completa."""
    partes = {
        "roic": _tramo(r["roic_mediana"], p["roic_ideal"], p["roic_aceptable"], 30),
        "crecimiento_ingresos": _tramo(r["cagr_ingresos"], p["crec_ideal"], p["crec_aceptable"], 20),
        # Si el EPS de hace 5 años era negativo no hay CAGR de 5 años: se usa el de 3.
        "crecimiento_eps": _tramo(r["cagr_eps"] if r["cagr_eps"] is not None else r["cagr_eps_3a"],
                                  p["crec_ideal"], p["crec_aceptable"], 15),
        "margen_bruto": _tramo(r["margen_bruto_ultimo"], p["margen_bruto_ideal"], p["margen_bruto_aceptable"], 10),
        "tendencia_margen": (10 if (r["margen_operativo_cambio"] or 0) >= 0 else
                             5 if (r["margen_operativo_cambio"] or 0) > -0.03 else 0),
        "fcf": 10 * (r["anios_fcf_positivo"] / r["anios_con_fcf"]) if r["anios_con_fcf"] else 0,
        "balance": (5 if r["caja_neta"] or (r["deuda_neta_ebitda"] is not None and r["deuda_neta_ebitda"] < 2)
                    else 2.5 if r["deuda_neta_ebitda"] is not None and r["deuda_neta_ebitda"] <= 3.5 else 0),
    }
    alertas = []
    if r["roic_mediana"] is not None and r["roic_mediana"] > 1.0:
        alertas.append("ROIC > 100%: capital invertido casi nulo (recompras o caja alta); validar el ROIC a mano")
    if (r["roe_cambio"] or 0) > 0.05 and (r["roa_cambio"] or 0) <= 0:
        alertas.append("ROE sube sin que suba ROA: crecimiento apalancado")
        partes["balance"] = max(0, partes["balance"] - 2.5)
    return {"total": round(sum(partes.values()), 1), "partes": partes, "alertas": alertas}
