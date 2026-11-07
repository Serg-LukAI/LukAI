"""Puente entre la ficha verificada (EDGAR) y el libro Excel de la skill lukai-equity-analyst.

Genera `Rubrica_Quality_Compounding.xlsx` con `build_rubrica.py` de la skill y llena automáticamente:
- Datos!B4:G23: 4 años fiscales + TTM (10-K + 10-Q) desde SEC EDGAR, y NTM si se pasan estimaciones.
- Comparables!C:E filas 6-12, 14 y 15 para los competidores (EDGAR; los múltiplos solo si hay precio).
Cada fila lleva su fuente (accession number) en la columna de notas.

El agente completa después solo lo cualitativo (hoja Cualitativo) y las estimaciones que falten.
"""
from __future__ import annotations

import json
import subprocess
import sys
from statistics import median

from . import edgar, metricas, red

SKILL = red.RAIZ / ".claude" / "skills" / "lukai-equity-analyst"
MM = 1e6

# fila de Datos -> (clave en la fila anual de metricas, es_monto)
FILAS = {
    5: ("ingresos", True), 6: ("utilidad_bruta", True), 7: ("ebitda", True), 8: ("ebit", True),
    9: ("utilidad_neta", True), 10: ("eps", False), 11: ("acciones", True), 12: ("flujo_operativo", True),
    13: ("capex", True), 14: ("fcf", True), 15: ("caja", True), 16: ("deuda", True), 17: ("patrimonio", True),
    18: ("activos", True), 19: ("tasa_impuesto", False), 21: ("arrendamientos", True),
}
FLUJOS_TTM = {"ingresos": "ingresos", "utilidad_bruta": "utilidad_bruta", "ebit": "utilidad_operativa",
              "utilidad_neta": "utilidad_neta", "eps": "eps_diluido", "flujo_operativo": "flujo_operativo",
              "capex": "capex", "dya": "dya", "acciones": None}
SALDOS_TTM = {"caja": "caja", "patrimonio": "patrimonio", "activos": "activos", "arrendamientos": "arrendamientos"}


def _r(x, monto):
    if x is None:
        return None
    return round(x / MM, 1) if monto else round(x, 4)


def columna_ttm(hechos: dict, series: dict, ult: dict) -> tuple[dict, str]:
    """Fila TTM: flujos = año fiscal + YTD − YTD previo; saldos = último trimestre. Devuelve (valores, hasta)."""
    cierre = ult["cierre"]
    v, hasta = {}, cierre
    for clave, concepto in FLUJOS_TTM.items():
        if concepto is None:
            continue
        valor_fy = series["conceptos"][concepto].get(cierre, {}).get("valor")
        t = edgar.ttm(hechos, concepto, cierre, valor_fy)
        v[clave] = t["valor"] if t else None
        if t and t["hasta"] > hasta:
            hasta = t["hasta"]
    if v.get("utilidad_bruta") is None and ult["margen_bruto"] is not None and v.get("ingresos"):
        v["utilidad_bruta"] = v["ingresos"] * ult["margen_bruto"]
    v["capex"] = None if v.get("capex") is None else abs(v["capex"])
    v["ebitda"] = None if v.get("ebit") is None else v["ebit"] + (v.get("dya") or ult.get("dya") or 0)
    v["fcf"] = None if v.get("flujo_operativo") is None else v["flujo_operativo"] - (v.get("capex") or 0)
    # Acciones: nivel del último periodo, NUNCA suma de trimestres (lección NVDA de la skill).
    v["acciones"] = ult["acciones"]
    for clave, concepto in SALDOS_TTM.items():
        s = edgar.ultimo_saldo(hechos, concepto)
        v[clave] = s["valor"] if s else ult.get(clave)
    if v.get("arrendamientos") is None:
        v["arrendamientos"] = ult.get("arrendamientos")
    inv = edgar.ultimo_saldo(hechos, "inversiones_cp")
    if v.get("caja") is not None and inv and inv["hasta"] == (edgar.ultimo_saldo(hechos, "caja") or {}).get("hasta"):
        v["caja"] += inv["valor"]
    v["deuda"] = ult["deuda"]  # la deuda financiera trimestral viene muy fragmentada en XBRL: se usa la del 10-K
    v["tasa_impuesto"] = ult["tasa_impuesto"]
    return v, hasta


def valores_datos(ticker: str, precio: float | None, wacc: float | None, precios_cierre: dict[str, float],
                  ntm: dict | None) -> tuple[dict, list[str]]:
    """JSON {Hoja:{Celda:valor}} para fill_rubrica.py y la lista de brechas."""
    cik = edgar.cik_de(ticker)
    hechos = edgar.hechos(cik)
    series = edgar.series_anuales(hechos)
    filas = metricas.anuales(series)[-4:]
    ult = filas[-1]
    ttm, hasta = columna_ttm(hechos, series, ult)
    cols = ["B", "C", "D", "E"][-len(filas):]
    datos: dict = {}
    brechas: list[str] = []
    for col, f in zip(cols, filas):
        datos[f"{col}4"] = f"FY{f['cierre'][:4]}"
    datos["F4"] = f"TTM {hasta}"
    datos["G4"] = f"NTM {int(hasta[:4]) + 1}E" if ntm else "NTM (sin estimado)"

    for fila, (clave, monto) in FILAS.items():
        for col, f in zip(cols, filas):
            val = _r(f.get(clave), monto)
            datos[f"{col}{fila}"] = val
            if val is None:
                brechas.append(f"Datos!{col}{fila} ({clave} {f['cierre']})")
        datos[f"F{fila}"] = _r(ttm.get(clave), monto)
        if datos[f"F{fila}"] is None:
            brechas.append(f"Datos!F{fila} ({clave} TTM)")
        conceptos = series["conceptos"]
        fuente = {
            "ingresos": "ingresos", "utilidad_bruta": "utilidad_bruta", "ebit": "utilidad_operativa",
            "utilidad_neta": "utilidad_neta", "eps": "eps_diluido", "flujo_operativo": "flujo_operativo",
            "capex": "capex", "caja": "caja", "patrimonio": "patrimonio", "activos": "activos",
            "arrendamientos": "arrendamientos", "acciones": "acciones_diluidas"}.get(clave)
        nota = "SEC EDGAR"
        if fuente and conceptos.get(fuente):
            ref = conceptos[fuente].get(ult["cierre"]) or next(iter(conceptos[fuente].values()))
            nota = f"SEC EDGAR {ref['forma']} accn {ref['accn']} ({ref['etiqueta']}); TTM hasta {hasta}"
        extra = {
            7: "EBITDA = EBIT operativo + D&A (no incluye ganancias de inversiones).",
            10: "Ajustado por splits a la base actual.",
            11: "TTM = nivel del último año, no suma de trimestres.",
            14: "FCF = OCF − |capex| (GAAP). Si hay float/no recurrentes, reemplazar por el ajustado citado.",
            16: "SOLO deuda financiera (sin arrendamientos operativos). TTM = último 10-K.",
            19: "Impuestos / utilidad antes de impuestos (21% si no es razonable).",
            21: "Pasivo por arrendamiento operativo: fuera de DN/EBITDA, dentro del capital invertido del ROIC.",
        }.get(fila, "")
        datos[f"H{fila}"] = f"{nota}. {extra}".strip()

    # Fila 20: precio de cierre de cada año fiscal (ajustado por splits), si hay histórico.
    for col, f in zip(cols, filas):
        previos = [k for k in precios_cierre if k <= f["cierre"]]
        datos[f"{col}20"] = round(precios_cierre[max(previos)], 2) if previos else None
        if not previos:
            brechas.append(f"Datos!{col}20 (precio de cierre FY{f['cierre'][:4]})")
    datos["H20"] = "Cierre mensual ajustado ≤ fin de año fiscal (Alpha Vantage TIME_SERIES_MONTHLY_ADJUSTED)."
    datos["B22"] = wacc
    datos["H22"] = "Tasa libre FRED DGS10 + prima de mercado (config/criterios.yaml)."
    datos["B23"] = precio
    if precio is None:
        brechas.append("Datos!B23 (precio actual)")

    # Columna G (NTM): estimados citados; el resto con márgenes TTM (receta de la skill), marcado como proyección.
    if ntm and ntm.get("ingresos"):
        ing = ntm["ingresos"]
        base = ttm.get("ingresos") or ult["ingresos"]
        def margen(clave):  # noqa: E306
            x = ttm.get(clave)
            return None if x is None or not base else x / base
        g = {"ingresos": ing, "utilidad_bruta": margen("utilidad_bruta"), "ebitda": margen("ebitda"),
             "ebit": margen("ebit"), "utilidad_neta": margen("utilidad_neta"), "flujo_operativo": margen("flujo_operativo"),
             "capex": margen("capex"), "fcf": margen("fcf")}
        for fila, (clave, monto) in FILAS.items():
            if clave in g and clave != "ingresos":
                datos[f"G{fila}"] = None if g[clave] is None else round(g[clave] * ing / MM, 1)
            elif clave == "ingresos":
                datos[f"G{fila}"] = round(ing / MM, 1)
            elif clave == "eps":
                datos[f"G{fila}"] = ntm.get("eps")
            else:
                datos[f"G{fila}"] = datos[f"F{fila}"]
        datos["G4"] = f"NTM {ntm.get('etiqueta', 'E')}"
    else:
        brechas.append("Datos!G5:G21 (NTM: pasar --ingresos-ntm y --eps-ntm citados)")
    return {"Datos": datos}, brechas


def valores_comparables(peers: list[str], precios_peers: dict[str, float]) -> dict:
    """Comparables!C:E desde EDGAR. Filas: 6 CAGR EPS, 7 m. bruto, 8 m. EBITDA, 9 ROE, 10 ROIC, 11 DN/EBITDA,
    12 P/E TTM, 14 EV/EBITDA, 15 FCF yield (estas 3 solo con precio). 5 y 13 (forward) quedan para el agente."""
    out: dict = {}
    columnas = {}
    for col, t in zip(["C", "D"], peers[:2]):
        cik = edgar.cik_de(t)
        _, series = edgar.series_compactas(cik)
        filas = metricas.anuales(series)
        r = metricas.resumen(filas)
        u = filas[-1]
        p = precios_peers.get(t.upper())
        mc = p * u["acciones"] if p and u["acciones"] else None
        ev = None if mc is None else mc + (u["deuda_neta"] or 0)
        v = {
            6: r["cagr_eps"], 7: u["margen_bruto"],
            8: None if not u["ebitda"] or not u["ingresos"] else u["ebitda"] / u["ingresos"],
            9: u["roe"], 10: u["roic"], 11: u["deuda_neta_ebitda"],
            12: None if not p or not u["eps"] or u["eps"] <= 0 else p / u["eps"],
            14: None if ev is None or not u["ebitda"] else ev / u["ebitda"],
            15: None if ev is None or u["fcf"] is None else u["fcf"] / ev,
        }
        if series["moneda"] != "USD":
            for k in (12, 14, 15):
                v[k] = None  # múltiplos con precio en USD y reportes en otra moneda: no comparables sin fx
        columnas[col] = v
        out[f"{col}4"] = t.upper()
        for fila, val in v.items():
            out[f"{col}{fila}"] = None if val is None else round(val, 4)
    for fila in (6, 7, 8, 9, 10, 11, 12, 14, 15):
        vals = [c[fila] for c in columnas.values() if c.get(fila) is not None]
        out[f"E{fila}"] = round(median(vals), 4) if vals else None
    out["E4"] = "Mediana peers"
    out["F5"] = ("C–E filas 6-12, 14, 15: SEC EDGAR (último 10-K/20-F) calculado por lukai; 5 y 13 (forward): "
                 "estimados citados. E = mediana de los competidores.")
    return {"Comparables": out}


SALIDA = {  # "Salida que leer" de reference/DATA_MAP.md
    "puntaje": ("Rúbrica", "B33"), "clasificacion": ("Rúbrica", "B35"), "calidad": ("Rúbrica", "E22"),
    "valoracion": ("Rúbrica", "E30"), "knockout": ("Rúbrica", "D11"), "momentum": ("Rúbrica", "B41"),
    "confianza": ("Rúbrica", "B42"), "foso": ("Cualitativo", "B25"), "veredicto_cualitativo": ("Cualitativo", "B26"),
    "ancla_multiplo": ("Valoración", "B12"), "valor_justo_pe_medio": ("Valoración", "B21"),
    "valor_fcf": ("Valoración", "B25"), "discrepancia": ("Valoración", "B29"),
    "valor_justo_conservador": ("Valoración", "B30"), "conclusion": ("Valoración", "B33"),
    "compra_desde": ("Valoración", "B35"), "compra_hasta": ("Valoración", "B36"),
}


def leer_resultados(xlsx: str) -> dict:
    """Recalcula una COPIA con LibreOffice (si está instalado) y lee solo las celdas de resultado.

    El archivo original no se toca: Excel lo recalcula al abrirlo y conserva gráficos y formatos.
    """
    import shutil
    import tempfile

    from openpyxl import load_workbook

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return {"aviso": "Sin LibreOffice: abre el .xlsx en Excel para ver los resultados (o replica las fórmulas)."}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", tmp, xlsx],
                       check=True, capture_output=True, timeout=180)
        wb = load_workbook(f"{tmp}/{xlsx.replace(chr(92), '/').split('/')[-1]}", data_only=True)
        out = {}
        for clave, (hoja, celda) in SALIDA.items():
            v = wb[hoja][celda].value
            out[clave] = round(v, 4) if isinstance(v, float) else v
        return out


def generar(ticker: str, salida: str, precio: float | None = None, wacc: float | None = None,
            precios_cierre: dict[str, float] | None = None, ntm: dict | None = None,
            peers: list[str] | None = None, precios_peers: dict[str, float] | None = None) -> dict:
    nombre = edgar.mapa_tickers()[ticker.upper()]["nombre"]
    subprocess.run([sys.executable, str(SKILL / "scripts" / "build_rubrica.py"), "--blank",
                    "--company", f"{nombre} ({ticker.upper()})", "--out", salida],
                   check=True, capture_output=True)
    valores, brechas = valores_datos(ticker, precio, wacc, precios_cierre or {}, ntm)
    if peers:
        valores.update(valores_comparables(peers, precios_peers or {}))
    else:
        brechas.append("Comparables (pasar --peers T1,T2)")
    ruta_json = salida.replace(".xlsx", "-valores.json")
    with open(ruta_json, "w", encoding="utf-8") as fh:
        json.dump(valores, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, str(SKILL / "scripts" / "fill_rubrica.py"), salida, ruta_json, "--no-recalc"],
                   check=True, capture_output=True)
    return {"xlsx": salida, "valores": ruta_json, "celdas": sum(len(v) for v in valores.values()),
            "brechas": brechas, "resultados": leer_resultados(salida)}


def completar(salida: str, json_extra: str) -> dict:
    """Escribe en el libro las celdas que aporta el agente (Cualitativo, K5, forward de comparables, FCF ajustado)
    y devuelve los resultados recalculados."""
    subprocess.run([sys.executable, str(SKILL / "scripts" / "fill_rubrica.py"), salida, json_extra, "--no-recalc"],
                   check=True, capture_output=True)
    return {"xlsx": salida, "resultados": leer_resultados(salida)}
