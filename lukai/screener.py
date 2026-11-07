"""Screener trimestral: universo → knockouts → puntaje de calidad → top N (+ precio solo para el top)."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import yaml

from . import edgar, metricas, precios, red, universo


def criterios() -> dict:
    return yaml.safe_load((red.RAIZ / "config" / "criterios.yaml").read_text())


def evaluar(empresa: dict, cfg: dict, refrescar: bool = False) -> dict:
    """Evalúa una empresa solo con datos de EDGAR (sin gastar cupo de Alpha Vantage)."""
    r = dict(empresa)
    try:
        sub, series = edgar.series_compactas(empresa["cik"], refrescar)
    except Exception as e:  # noqa: BLE001
        r.update(estado="error", detalle=f"EDGAR: {e}")
        return r
    r.update(sic=sub.get("sic"), sector=sub.get("sicDescription"), moneda=series.get("moneda"))
    if universo.excluido_por_sic(sub.get("sic")):
        r.update(estado="excluida", detalle="Financiera (SIC 6000-6799): analizar a mano con /analizar")
        return r
    filas = metricas.anuales(series)
    res = metricas.resumen(filas)
    r["resumen"] = res
    r["ultimo_filing"] = series["conceptos"]["ingresos"].get(series["cierres"][-1], {}).get("accn") if series["cierres"] else None
    ko = metricas.knockouts(res, cfg["knockouts"]) if res else ["Sin datos anuales en EDGAR"]
    if ko:
        r.update(estado="knockout", detalle="; ".join(ko))
        return r
    pts = metricas.puntaje_calidad(res, cfg["puntaje"])
    r.update(estado="aprobada", puntaje=pts["total"], partes=pts["partes"], alertas=pts["alertas"],
             eps_ultimo=filas[-1]["eps"])
    return r


def ejecutar(top: int | None = None, con_precios: bool = True, refrescar: bool = False, hilos: int = 4,
             solo: list[str] | None = None) -> dict:
    cfg = criterios()
    top = top or cfg["screener"]["top"]
    empresas = universo.construir()
    if solo:
        pedidos = {s.strip().upper() for s in solo}
        empresas = [e for e in empresas if pedidos & set(e.get("clases", [e["ticker"]]))]
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        resultados = list(ex.map(lambda e: evaluar(e, cfg, refrescar), empresas))

    # Desempate entre puntajes iguales: ROIC mediano (calidad del negocio) y luego crecimiento de ingresos.
    aprobadas = sorted((r for r in resultados if r["estado"] == "aprobada"),
                       key=lambda r: (-r["puntaje"], -(r["resumen"]["roic_mediana"] or 0),
                                      -(r["resumen"]["cagr_ingresos"] or 0)))
    finalistas = [r for r in aprobadas if r["puntaje"] >= cfg["screener"]["puntaje_minimo"]][:top]
    # Las ideas manuales siempre se muestran, aunque no estén en el top.
    ideas = [r for r in resultados if r.get("idea") and r not in finalistas]

    if con_precios:
        for r in finalistas:
            try:
                p = precios.precio(r["ticker"])
                r["precio"] = p
                if r.get("moneda") == "USD" and r.get("eps_ultimo") and r["eps_ultimo"] > 0:
                    r["pe_ttm"] = p["precio"] / r["eps_ultimo"]
            except Exception as e:  # noqa: BLE001
                r["precio"] = {"error": str(e)}

    salida = {
        "fecha": date.today().isoformat(),
        "universo": len(empresas),
        "conteo": {k: sum(1 for r in resultados if r["estado"] == k)
                   for k in ("aprobada", "knockout", "excluida", "error")},
        "finalistas": finalistas,
        "ideas": ideas,
        "llamadas": dict(red.estadisticas),
    }
    destino = red.RAIZ / "data" / "screens"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{salida['fecha']}.json").write_text(json.dumps(salida, indent=1, ensure_ascii=False, default=str))
    (destino / f"{salida['fecha']}.md").write_text(a_markdown(salida))
    return salida


def _pct(x):
    if x is None:
        return "s/d"
    return ">100%" if x > 1 else f"{x:.0%}"


def a_markdown(s: dict) -> str:
    c = s["conteo"]
    lineas = [
        f"# Screener {s['fecha']}",
        "",
        f"Universo {s['universo']} · aprobadas {c['aprobada']} · knockout {c['knockout']} · "
        f"financieras excluidas {c['excluida']} · errores {c['error']}",
        f"Requests a la red: {s['llamadas']['red']} · desde caché: {s['llamadas']['cache']}",
        "",
        "Fuente de fundamentales: SEC EDGAR (10-K / 20-F). El puntaje ordena candidatos; el veredicto sale de /analizar.",
        "",
        "| # | Ticker | Empresa | Puntaje | ROIC med. | CAGR ingresos | CAGR EPS | Margen bruto | DN/EBITDA | P/E TTM | Precio |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(s["finalistas"], 1):
        res = r["resumen"]
        p = r.get("precio") or {}
        precio_txt = (f"{p['precio']:.2f} ({p['fuente']}{'' if p.get('verificado') else ' ⚠️'})"
                      if "precio" in p else "s/d")
        dn = res["deuda_neta_ebitda"]
        dn_txt = "caja neta" if res["caja_neta"] else ("s/d" if dn is None else f"{dn:.1f}x")
        pe = r.get("pe_ttm")
        pe_txt = "s/d" if pe is None else f"{pe:.1f}"
        lineas.append(
            f"| {i} | {r['ticker']} | {r['nombre'][:28]} | {r['puntaje']} | {_pct(res['roic_mediana'])} | "
            f"{_pct(res['cagr_ingresos'])} | {_pct(res['cagr_eps'])} | {_pct(res['margen_bruto_ultimo'])} | "
            f"{dn_txt} | {pe_txt} | {precio_txt} |")
    alertas = [(r["ticker"], a) for r in s["finalistas"] for a in r.get("alertas", [])]
    if alertas:
        lineas += ["", "Alertas:"] + [f"- {t}: {a}" for t, a in alertas]
    if s["ideas"]:
        lineas += ["", "## Ideas manuales (ideas.md)", ""]
        for r in s["ideas"]:
            extra = f"puntaje {r['puntaje']}" if r["estado"] == "aprobada" else r.get("detalle", "")
            lineas.append(f"- **{r['ticker']}** — {r['estado']}: {extra}")
    return "\n".join(lineas) + "\n"
