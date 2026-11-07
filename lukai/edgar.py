"""SEC EDGAR: fuente principal, oficial y gratuita, para estados financieros.

Cubre los 10-K (US-GAAP) y también los 20-F/40-F de emisores extranjeros (IFRS), como SAP, ASML o TSM.
Cada valor devuelto conserva el accession number del filing del que sale, para poder citarlo.
"""
from __future__ import annotations

from datetime import date

from . import red

BASE = "https://data.sec.gov"
VERSION_SERIES = 2  # subir si cambia la extracción, para invalidar los resúmenes guardados
FORMAS_ANUALES = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A", "10-KT"}

# Concepto -> etiquetas XBRL en orden de prioridad (US-GAAP e IFRS).
# Las empresas cambian de etiqueta con los años: por cada fecha de cierre se toma la primera que tenga valor.
CONCEPTOS: dict[str, tuple[str, list[str]]] = {
    "ingresos": ("flujo", [
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
        "Revenue", "RevenueFromContractsWithCustomers"]),
    "costo_ventas": ("flujo", ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfSales"]),
    "utilidad_bruta": ("flujo", ["GrossProfit"]),
    "utilidad_operativa": ("flujo", ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"]),
    "utilidad_neta": ("flujo", ["NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]),
    "eps_diluido": ("flujo", ["EarningsPerShareDiluted", "DilutedEarningsLossPerShare",
                              "BasicAndDilutedEarningsLossPerShare"]),
    "flujo_operativo": ("flujo", [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "CashFlowsFromUsedInOperatingActivities"]),
    "capex": ("flujo", [
        "PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "PurchaseOfPropertyPlantAndEquipment",
        "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets"]),
    "dya": ("flujo", [
        "DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization", "AdjustmentsForDepreciationAndAmortisationExpense",
        "DepreciationAndAmortisationExpense", "Depreciation"]),
    "utilidad_antes_impuestos": ("flujo", [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "ProfitLossBeforeTax"]),
    "impuestos": ("flujo", ["IncomeTaxExpenseBenefit", "IncomeTaxExpenseContinuingOperations"]),
    "acciones_diluidas": ("flujo", [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "AdjustedWeightedAverageShares", "WeightedAverageShares"]),
    "patrimonio": ("saldo", [
        "StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "EquityAttributableToOwnersOfParent", "Equity"]),
    "activos": ("saldo", ["Assets"]),
    "caja": ("saldo", [
        "CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalents"]),
    "inversiones_cp": ("saldo", ["MarketableSecuritiesCurrent", "ShortTermInvestments",
                                 "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]),
    "deuda_total_lp": ("saldo", ["LongTermDebt", "Borrowings"]),
    "deuda_lp_no_corriente": ("saldo", ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations",
                                        "LongtermBorrowings", "NoncurrentPortionOfNoncurrentBorrowings"]),
    "deuda_lp_corriente": ("saldo", ["LongTermDebtCurrent", "CurrentPortionOfLongtermBorrowings",
                                     "CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings"]),
    "deuda_cp": ("saldo", ["ShortTermBorrowings", "CommercialPaper", "ShorttermBorrowings"]),
}


def mapa_tickers() -> dict[str, dict]:
    """ticker -> {cik, nombre, bolsa}. Un request, caché de 7 días."""
    d = red.obtener_json("https://www.sec.gov/files/company_tickers_exchange.json", ttl_horas=24 * 7)
    campos = d["fields"]
    out = {}
    for fila in d["data"]:
        r = dict(zip(campos, fila))
        out.setdefault(r["ticker"].upper(), {"cik": int(r["cik"]), "nombre": r["name"], "bolsa": r["exchange"]})
    return out


def cik_de(ticker: str) -> int:
    m = mapa_tickers()
    t = ticker.upper().replace(".", "-")
    if t not in m:
        raise KeyError(f"{ticker} no aparece en EDGAR (¿no registra filings en la SEC?)")
    return m[t]["cik"]


def presentaciones(cik: int) -> dict:
    """Metadatos de la empresa: SIC, nombre, año fiscal, filings recientes. Caché de 7 días."""
    return red.obtener_json(f"{BASE}/submissions/CIK{cik:010d}.json", ttl_horas=24 * 7)


def hechos(cik: int, refrescar: bool = False, guardar: bool = True) -> dict:
    """Todos los hechos XBRL de la empresa. Caché de 90 días (un filing anual nuevo sale como mucho cada trimestre)."""
    return red.obtener_json(f"{BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json",
                            ttl_horas=0 if refrescar else 24 * 90, guardar=guardar)


def ultimo_anual(sub: dict) -> dict | None:
    """Último 10-K/20-F/40-F presentado según `submissions` (accession y fecha)."""
    rec = sub.get("filings", {}).get("recent", {})
    for forma, accn, fecha in zip(rec.get("form", []), rec.get("accessionNumber", []), rec.get("filingDate", [])):
        if forma in FORMAS_ANUALES:
            return {"forma": forma, "accn": accn, "fecha": fecha}
    return None


def series_compactas(cik: int, refrescar: bool = False) -> tuple[dict, dict]:
    """(submissions, series anuales) usando un resumen compacto en disco.

    El JSON completo de companyfacts (cientos de KB a varios MB) solo se descarga si apareció un filing anual
    nuevo desde la última vez; si no, se reutiliza el resumen (~10 KB). Así una corrida trimestral solo baja
    de nuevo a las empresas que publicaron 10-K/20-F.
    """
    import json

    sub = presentaciones(cik)
    ult = ultimo_anual(sub)
    ruta = red.CACHE / "series" / f"{cik}.json"
    if not refrescar and ruta.exists():
        guardado = json.loads(ruta.read_text())
        vigente = guardado.get("version") == VERSION_SERIES
        if vigente and (ult is None or guardado.get("ultimo_anual") == ult["accn"]):
            red.estadisticas["cache"] += 1
            return sub, guardado["series"]
    series = series_anuales(hechos(cik, refrescar=True, guardar=False))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"version": VERSION_SERIES, "ultimo_anual": ult and ult["accn"], "series": series}))
    return sub, series


def float_publico(periodos: list[str]) -> dict[int, dict]:
    """Float público (USD) de TODAS las empresas en uno o varios periodos 'frames'. 1 request por periodo."""
    out: dict[int, dict] = {}
    for p in periodos:
        try:
            d = red.obtener_json(f"{BASE}/api/xbrl/frames/dei/EntityPublicFloat/USD/{p}.json", ttl_horas=24 * 30)
        except Exception:
            continue
        for x in d["data"]:
            prev = out.get(x["cik"])
            if prev is None or x["end"] > prev["end"]:
                out[x["cik"]] = {"float": x["val"], "end": x["end"], "nombre": x["entityName"], "accn": x["accn"]}
    return out


def _dias(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _serie_etiqueta(facts: dict, etiqueta: str, tipo: str) -> tuple[dict[str, dict], str | None]:
    for tax in ("us-gaap", "ifrs-full"):
        nodo = facts.get(tax, {}).get(etiqueta)
        if not nodo:
            continue
        # Algunas etiquetas traen unidades vacías (p. ej. 'pure'); se usa la que tenga más datos.
        unidad = max(nodo["units"], key=lambda u: len(nodo["units"][u]))
        serie: dict[str, dict] = {}
        for x in nodo["units"][unidad]:
            if x.get("form") not in FORMAS_ANUALES:
                continue
            if tipo == "flujo":
                if "start" not in x or not 330 <= _dias(x["start"], x["end"]) <= 400:
                    continue
            prev = serie.get(x["end"])
            if prev is None or x["filed"] > prev["presentado"]:
                serie[x["end"]] = {"valor": x["val"], "accn": x["accn"], "forma": x["form"],
                                   "presentado": x["filed"], "etiqueta": f"{tax}:{etiqueta}"}
        if serie:
            return serie, unidad
    return {}, None


FORMAS_TRIMESTRALES = {"10-Q", "10-Q/A", "6-K"}


def ttm(facts_json: dict, concepto: str, cierre_fy: str, valor_fy: float | None) -> dict | None:
    """Últimos doce meses = año fiscal + acumulado del año en curso − mismo acumulado del año anterior.

    Usa los 10-Q (los 6-K de extranjeros rara vez traen XBRL). Si no hay trimestre posterior al cierre fiscal,
    el TTM es el propio año fiscal.
    """
    if valor_fy is None:
        return None
    tipo, etiquetas = CONCEPTOS[concepto]
    if tipo != "flujo":
        return None
    facts = facts_json.get("facts", {})
    for et in etiquetas:
        for tax in ("us-gaap", "ifrs-full"):
            nodo = facts.get(tax, {}).get(et)
            if not nodo:
                continue
            unidad = max(nodo["units"], key=lambda u: len(nodo["units"][u]))
            datos = [x for x in nodo["units"][unidad]
                     if x.get("form") in FORMAS_TRIMESTRALES and "start" in x]
            posteriores = [x for x in datos if x["end"] > cierre_fy and abs(_dias(cierre_fy, x["start"])) <= 7]
            if not posteriores:
                continue
            ytd = max(posteriores, key=lambda x: (x["end"], x["filed"]))
            previo = [x for x in datos if abs(_dias(x["end"], ytd["end"]) - 365) <= 10
                      and abs(_dias(x["start"], ytd["start"]) - 365) <= 10]
            if not previo:
                continue
            prev = max(previo, key=lambda x: x["filed"])
            return {"valor": valor_fy + ytd["val"] - prev["val"], "hasta": ytd["end"], "accn": ytd["accn"],
                    "etiqueta": f"{tax}:{et}"}
    return {"valor": valor_fy, "hasta": cierre_fy, "accn": None, "etiqueta": "año fiscal (sin 10-Q posterior)"}


def series_anuales(facts_json: dict, anios: int = 6) -> dict:
    """Series anuales por concepto, alineadas a las fechas de cierre fiscal de los ingresos.

    Devuelve {"cierres": [...], "moneda": "USD", "conceptos": {nombre: {cierre: {valor, accn, ...}}}}.
    """
    facts = facts_json.get("facts", {})
    crudo: dict[str, dict[str, dict]] = {}
    moneda = None
    for nombre, (tipo, etiquetas) in CONCEPTOS.items():
        combinado: dict[str, dict] = {}
        for et in etiquetas:
            serie, unidad = _serie_etiqueta(facts, et, tipo)
            for fin, v in serie.items():
                combinado.setdefault(fin, v)
            if nombre == "ingresos" and unidad and moneda is None:
                moneda = unidad
        crudo[nombre] = combinado

    cierres = sorted(crudo["ingresos"])[-anios:]
    # Saldos: a veces el cierre del balance difiere 1-3 días del de resultados; se empareja con tolerancia.
    conceptos = {}
    for nombre, serie in crudo.items():
        alineada = {}
        for c in cierres:
            if c in serie:
                alineada[c] = serie[c]
                continue
            cercanos = [k for k in serie if abs(_dias(k, c)) <= 7]
            if cercanos:
                alineada[c] = serie[cercanos[0]]
        conceptos[nombre] = alineada
    return {"cierres": cierres, "moneda": moneda, "conceptos": conceptos}
