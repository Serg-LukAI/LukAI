"""Ficha de datos para /analizar: todo lo numérico de una empresa, con fuente y filing por cifra.

El equity-analyst y el valuador trabajan SOBRE esta ficha. No calculan ratios a mano ni inventan cifras:
si algo no está aquí, se escribe "sin dato".
"""
from __future__ import annotations

import json
from datetime import date

from . import edgar, fred, metricas, precios, red, valuacion
from .screener import criterios

CLAVES_VERIFICACION = ("ingresos", "eps")
TOLERANCIA = 0.02


def av_desde_archivo(ruta: str) -> dict:
    """Lee la respuesta de Alpha Vantage INCOME_STATEMENT guardada en disco (el conector MCP guarda las
    respuestas grandes en un archivo). Así la verificación no carga 80 KB de JSON en el contexto del agente."""
    d = json.loads(open(ruta, encoding="utf-8").read())
    out = {"ingresos": {}, "utilidad_neta": {}, "ebit": {}}
    for r in d.get("annualReports", []):
        for clave, campo in (("ingresos", "totalRevenue"), ("utilidad_neta", "netIncome"), ("ebit", "operatingIncome")):
            if r.get(campo) not in (None, "None"):
                out[clave][r["fiscalDateEnding"]] = float(r[campo])
    return out


def verificar_cruzado(ticker: str, filas: list[dict], av: dict | None = None, fuente: str = "Alpha Vantage") -> dict:
    """Compara EDGAR con Alpha Vantage. Diferencia > 2% → ⚠️ para revisar contra el 10-K/20-F."""
    if av is None:
        try:
            av = precios.fundamentales_av(ticker)
        except Exception as e:  # noqa: BLE001
            return {"estado": "no realizada", "motivo": str(e)}
    hallazgos = []
    for f in filas:
        for clave in av:
            ed = f.get(clave)
            # Alpha Vantage etiqueta el año por fin de mes; EDGAR por la fecha exacta (años de 52/53 semanas).
            cand = [v for k, v in av[clave].items() if abs((date.fromisoformat(k) - date.fromisoformat(f["cierre"])).days) <= 15]
            if ed is None or not cand or cand[0] == 0:
                continue
            dif = abs(ed - cand[0]) / abs(cand[0])
            hallazgos.append({"cierre": f["cierre"], "metrica": clave, "edgar": ed, "alpha_vantage": cand[0],
                              "diferencia": round(dif, 4), "alerta": dif > TOLERANCIA})
    alertas = [h for h in hallazgos if h["alerta"]]
    return {"estado": "realizada", "fuente": fuente, "comparadas": len(hallazgos),
            "max_diferencia": max((h["diferencia"] for h in hallazgos), default=None),
            "alertas": alertas}


def cargar_historico(ruta: str) -> list[tuple[str, float]]:
    """Lee un histórico mensual guardado por el agente: respuesta de Alpha Vantage
    TIME_SERIES_MONTHLY_ADJUSTED (JSON) o una lista [[fecha, precio], ...]."""
    txt = open(ruta, encoding="utf-8").read()
    if not txt.lstrip().startswith(("{", "[")):
        # CSV de Alpha Vantage: timestamp,...,adjusted close,... o simplemente fecha,precio
        import csv
        import io
        filas = list(csv.reader(io.StringIO(txt.strip())))
        cab = [c.strip().lower() for c in filas[0]]
        if "timestamp" in cab:
            i = cab.index("adjusted close") if "adjusted close" in cab else cab.index("close")
            return sorted((f[0], float(f[i])) for f in filas[1:] if f)
        return sorted((f[0], float(f[1])) for f in filas if f and f[1].replace(".", "", 1).isdigit())
    d = json.loads(txt)
    if isinstance(d, dict):
        serie = d.get("Monthly Adjusted Time Series") or d.get("Monthly Time Series") or d
        return sorted((k, float(v.get("5. adjusted close") or v.get("4. close"))) for k, v in serie.items())
    return sorted((str(f), float(p)) for f, p in d)


def construir(ticker: str, valor_cartera: float | None = None, fx: float = 1.0, ratio_adr: float = 1.0,
              fcf_manual: float | None = None, refrescar: bool = False, precio_manual: dict | None = None,
              historico: list[tuple[str, float]] | None = None, fuente_historico: str = "archivo del agente",
              av_income: str | None = None) -> dict:
    cfg = criterios()
    cik = edgar.cik_de(ticker)
    sub = edgar.presentaciones(cik)
    hechos = edgar.hechos(cik, refrescar=refrescar)
    series = edgar.series_anuales(hechos)
    filas = metricas.anuales(series)
    res = metricas.resumen(filas)
    ko = metricas.knockouts(res, cfg["knockouts"])
    pts = metricas.puntaje_calidad(res, cfg["puntaje"])

    fuentes = {c: {cierre: {k: v[k] for k in ("accn", "forma", "etiqueta")} for cierre, v in s.items()}
               for c, s in series["conceptos"].items() if s}
    ficha: dict = {
        "ticker": ticker.upper(), "cik": cik, "nombre": sub.get("name"), "sector": sub.get("sicDescription"),
        "sic": sub.get("sic"), "moneda_reportes": series["moneda"], "fecha": date.today().isoformat(),
        "anual": filas, "resumen": res, "knockouts_mecanicos": ko, "puntaje_calidad": pts,
        "fuentes_por_cifra": fuentes, "avisos": [],
    }
    if series["moneda"] != "USD":
        ficha["avisos"].append(
            f"Reporta en {series['moneda']}. Para valorar por ADR se usa fx={fx} USD por {series['moneda']} y "
            f"ratio_adr={ratio_adr} acciones ordinarias por ADR: confírmalos antes de aceptar la valoración.")

    # Precio y múltiplos
    if precio_manual:
        p = precio_manual
        ficha["precio"] = p
    else:
        try:
            p = precios.precio(ticker)
            ficha["precio"] = p
        except Exception as e:  # noqa: BLE001
            ficha["precio"] = {"error": str(e)}
            p = None
    ult = filas[-1]
    eps_usd_adr = None if ult["eps"] is None else ult["eps"] * fx * ratio_adr
    if p and eps_usd_adr and eps_usd_adr > 0:
        ficha["pe_ttm"] = p["precio"] / eps_usd_adr
    try:
        hist, fuente_hist = (historico, fuente_historico) if historico else precios.historico_mensual(ticker)
        eps_anual = {f["cierre"]: f["eps"] * fx * ratio_adr for f in filas if f["eps"] is not None}
        ficha["pe_mediana_5a"] = {"valor": valuacion.mediana_pe(hist, eps_anual), "fuente": fuente_hist}
    except Exception as e:  # noqa: BLE001
        ficha["pe_mediana_5a"] = {"valor": None, "motivo": str(e)}

    # Últimos doce meses (10-Q): base más actual que el año fiscal cerrado.
    ttm_vals = {}
    for concepto in ("ingresos", "utilidad_operativa", "eps_diluido", "flujo_operativo", "capex"):
        valor_fy = series["conceptos"][concepto].get(ult["cierre"], {}).get("valor")
        ttm_vals[concepto] = edgar.ttm(hechos, concepto, ult["cierre"], valor_fy)
    fcf_ttm = None
    if ttm_vals["flujo_operativo"] and ttm_vals["flujo_operativo"]["valor"] is not None:
        capex = ttm_vals["capex"]["valor"] if ttm_vals["capex"] else 0
        fcf_ttm = ttm_vals["flujo_operativo"]["valor"] - abs(capex or 0)
    ficha["ttm"] = {**ttm_vals, "fcf": fcf_ttm}
    eps_ttm = ttm_vals["eps_diluido"]["valor"] if ttm_vals["eps_diluido"] else None
    if p and eps_ttm and eps_ttm > 0:
        ficha["pe_ttm"] = p["precio"] / (eps_ttm * fx * ratio_adr)

    # Tasa de descuento (FRED) y valoración
    v = cfg["valoracion"]
    try:
        rf = fred.tasa_libre_riesgo()
    except Exception as e:  # noqa: BLE001
        rf = {"valor": 0.045, "fuente": f"supuesto 4.5% (FRED no disponible: {e})"}
    tasa = valuacion.wacc(rf["valor"], prima_mercado=v["prima_mercado"])
    if fcf_manual is not None:
        fcf0, origen = fcf_manual, "manual (ajustado por el analista)"
    elif fcf_ttm is not None and ttm_vals["flujo_operativo"]["hasta"] != ult["cierre"]:
        fcf0, origen = fcf_ttm, f"FCF TTM hasta {ttm_vals['flujo_operativo']['hasta']} (10-K + 10-Q)"
    else:
        fcf0, origen = ult["fcf"], f"FCF último año fiscal ({ult['cierre']})"
    val: dict = {"tasa_libre": rf, "tasa_descuento": tasa, "fcf_base": fcf0, "fcf_base_origen": origen}
    if p and fcf0 and fcf0 > 0 and ult["acciones"]:
        acciones_adr = ult["acciones"] / ratio_adr
        fcf_usd = fcf0 * fx
        deuda_neta_usd = (ult["deuda_neta"] or 0) * fx
        ve = p["precio"] * acciones_adr + deuda_neta_usd
        crec_hist = [res["cagr_ingresos"], res["cagr_eps"],
                     metricas.cagr(filas[0]["fcf"], ult["fcf"], len(filas) - 1)]
        g = valuacion.crecimiento_conservador(crec_hist, v["recorte_crecimiento"], v["tope_crecimiento"])
        val["crecimiento_implicito_reverse_dcf"] = valuacion.reverse_dcf(ve, fcf_usd, tasa, v["crecimiento_terminal"])
        val["crecimientos_historicos"] = crec_hist
        val["crecimiento_conservador"] = g
        if g is not None:
            justo = valuacion.valor_justo_por_accion(fcf_usd, acciones_adr, deuda_neta_usd, g, tasa,
                                                     v["crecimiento_terminal"])
            entrada = valuacion.precio_entrada(justo, v["margen_seguridad"])
            val.update(valor_justo_conservador=justo, precio_entrada=entrada,
                       semaforo=valuacion.semaforo(p["precio"], entrada, justo))
    else:
        val["aviso"] = "Sin valoración automática: falta precio, FCF positivo o número de acciones."
    ficha["valoracion"] = val
    if valor_cartera:
        c = cfg["cartera"]
        ficha["tramos"] = valuacion.tramos(valor_cartera, c["techo_posicion"], tuple(c["tramos"]))

    if av_income:
        ficha["verificacion_cruzada"] = verificar_cruzado(ticker, filas, av_desde_archivo(av_income),
                                                          "Alpha Vantage INCOME_STATEMENT (conector MCP)")
    else:
        ficha["verificacion_cruzada"] = verificar_cruzado(ticker, filas)
    ficha["llamadas"] = dict(red.estadisticas)

    destino = red.RAIZ / "analisis" / ticker.upper()
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{ficha['fecha']}-ficha.json").write_text(json.dumps(ficha, indent=1, ensure_ascii=False, default=str))
    return ficha


def _m(x, moneda="", escala=1e9, sufijo=" mil M"):
    return "s/d" if x is None else f"{x / escala:,.1f}{sufijo}{(' ' + moneda) if moneda else ''}"


def _p(x):
    return "s/d" if x is None else f"{x:.1%}"


def resumen_texto(f: dict) -> str:
    """Vista compacta de la ficha (lo que el agente lee; el JSON completo queda en disco)."""
    r, mon = f["resumen"], f["moneda_reportes"]
    v = f.get("valoracion", {})
    pr = f.get("precio") or {}
    lineas = [
        f"# {f['ticker']} — {f['nombre']} ({f['sector']}) · {f['fecha']}",
        f"Moneda de reportes: {mon} · Fuente: SEC EDGAR, CIK {f['cik']}",
        "",
        "| Cierre | Ingresos | EBIT | EPS | FCF | ROIC | M. bruto | M. oper. | DN/EBITDA |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for a in f["anual"]:
        dn = a["deuda_neta_ebitda"]
        lineas.append(f"| {a['cierre']} | {_m(a['ingresos'])} | {_m(a['ebit'])} | "
                      f"{'s/d' if a['eps'] is None else round(a['eps'], 2)} | {_m(a['fcf'])} | {_p(a['roic'])} | "
                      f"{_p(a['margen_bruto'])} | {_p(a['margen_operativo'])} | "
                      f"{'s/d' if dn is None else f'{dn:.1f}x'} |")
    t = f.get("ttm", {})
    ing_ttm = (t.get("ingresos") or {}).get("valor")
    lineas += [
        "",
        f"TTM hasta {(t.get('ingresos') or {}).get('hasta', 's/d')}: ingresos {_m(ing_ttm)}, FCF {_m(t.get('fcf'))}, "
        f"EPS {(t.get('eps_diluido') or {}).get('valor', 's/d')}",
        f"CAGR ingresos {_p(r['cagr_ingresos'])} ({r['anios'] - 1} a) · CAGR {r['eps_fuente']} {_p(r['cagr_eps'])} · "
        f"ROIC mediano {_p(r['roic_mediana'])} · FCF positivo {r['anios_fcf_positivo']}/{r['anios_con_fcf']} años",
        f"Knockouts mecánicos: {'; '.join(f['knockouts_mecanicos']) or 'ninguno'}",
        f"Puntaje de calidad (screener): {f['puntaje_calidad']['total']}/100 · alertas: "
        f"{'; '.join(f['puntaje_calidad']['alertas']) or 'ninguna'}",
        "",
        f"Precio: {pr.get('precio', 's/d')} ({pr.get('fuente', pr.get('error', ''))}, {pr.get('fecha', '')})"
        + ("" if pr.get("verificado", True) else " ⚠️ no verificado"),
        f"P/E TTM {'s/d' if f.get('pe_ttm') is None else round(f['pe_ttm'], 1)} · "
        f"P/E mediana 5a {'s/d' if not f['pe_mediana_5a'].get('valor') else round(f['pe_mediana_5a']['valor'], 1)}",
        f"Tasa de descuento {_p(v.get('tasa_descuento'))} (10a {_p(v['tasa_libre']['valor'])} {v['tasa_libre']['fuente']}) · "
        f"FCF base: {v.get('fcf_base_origen')}",
    ]
    if "valor_justo_conservador" in v:
        lineas.append(
            f"Reverse DCF: el precio descuenta {_p(v['crecimiento_implicito_reverse_dcf'])} anual de FCF · "
            f"crecimiento conservador {_p(v['crecimiento_conservador'])} → valor justo {v['valor_justo_conservador']:.2f} · "
            f"entrada {v['precio_entrada']:.2f} · semáforo {v['semaforo']}")
    elif v.get("aviso"):
        lineas.append(v["aviso"])
    if f.get("tramos"):
        tr = f["tramos"]
        lineas.append(f"Techo 5%: {tr['techo']} USD · tramos {tr['tramos']}")
    vc = f["verificacion_cruzada"]
    if vc["estado"] == "realizada":
        lineas.append(f"Verificación cruzada ({vc['fuente']}): {vc['comparadas']} cifras, diferencia máx. "
                      f"{_p(vc['max_diferencia'])}, alertas {len(vc['alertas'])}")
        lineas += [f"  ⚠️ {a['cierre']} {a['metrica']}: EDGAR {a['edgar']:,.0f} vs AV {a['alpha_vantage']:,.0f}"
                   for a in vc["alertas"]]
    else:
        lineas.append(f"Verificación cruzada: no realizada ({vc['motivo']})")
    lineas += [f"Aviso: {a}" for a in f["avisos"]]
    lineas.append(f"Requests a la red: {f['llamadas']['red']} · desde caché: {f['llamadas']['cache']}")
    return "\n".join(lineas)
