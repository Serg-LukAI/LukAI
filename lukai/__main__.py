"""Línea de comandos de LukAI. Uso: python -m lukai <comando> [opciones]

  screen   [--top N] [--sin-precios] [--refrescar] [--solo T1,T2]   Screener trimestral
  ficha    TICKER [--cartera USD] [--fx X] [--adr N] [--fcf USD]     Datos verificados para /analizar
  precio   T1 [T2 ...]                                              Precio con ruta de fuentes
  semaforo --precio P --entrada E --justo J [--cartera USD]         Semáforo y tramos (reglas de Watchlist)
  macro                                                             Tasa 10 años y S&P 500 (FRED)
  llamadas                                                          Requests hechos hoy por fuente
"""
from __future__ import annotations

import argparse
import json
import sys

from . import fred, precios, red, valuacion


def _imprimir(obj) -> None:
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lukai", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("screen")
    s.add_argument("--top", type=int)
    s.add_argument("--sin-precios", action="store_true")
    s.add_argument("--refrescar", action="store_true")
    s.add_argument("--solo", help="Lista de tickers separados por coma (prueba rápida)")
    s.add_argument("--hilos", type=int, default=4)

    f = sp.add_parser("ficha")
    f.add_argument("ticker")
    f.add_argument("--cartera", type=float, help="Valor total de la cartera en USD (para techo y tramos)")
    f.add_argument("--fx", type=float, default=1.0, help="USD por unidad de la moneda de reporte (emisores extranjeros)")
    f.add_argument("--adr", type=float, default=1.0, help="Acciones ordinarias por ADR")
    f.add_argument("--fcf", type=float, help="FCF base ajustado (moneda de reporte), si el GAAP no es representativo")
    f.add_argument("--refrescar", action="store_true")
    f.add_argument("--precio", type=float, help="Precio obtenido por el agente (p. ej. conector Alpha Vantage)")
    f.add_argument("--fecha-precio", help="Fecha del precio manual (AAAA-MM-DD)")
    f.add_argument("--fuente-precio", default="Alpha Vantage (conector MCP)")
    f.add_argument("--historico", help="Precios mensuales: CSV fecha,precio o respuesta de TIME_SERIES_MONTHLY_ADJUSTED")
    f.add_argument("--av-income", help="Archivo con la respuesta de Alpha Vantage INCOME_STATEMENT (verificación cruzada)")

    rb = sp.add_parser("rubrica", help="Genera y llena el Excel de la skill lukai-equity-analyst desde EDGAR")
    rb.add_argument("ticker")
    rb.add_argument("--precio", type=float)
    rb.add_argument("--historico", help="Precios mensuales ajustados (CSV o JSON de Alpha Vantage) para la fila 20")
    rb.add_argument("--ingresos-ntm", type=float, help="Ingresos NTM estimados en USD (no en millones)")
    rb.add_argument("--eps-ntm", type=float)
    rb.add_argument("--etiqueta-ntm", default="E", help="Texto del encabezado NTM, p. ej. '2027E (AV EARNINGS_ESTIMATES)'")
    rb.add_argument("--peers", help="Dos competidores, separados por coma")
    rb.add_argument("--precios-peers", help="Precios de los competidores: T1=123.4,T2=56.7")
    rb.add_argument("--out", help="Ruta del .xlsx (por defecto analisis/<TICKER>/<fecha>-rubrica.xlsx)")

    cp_ = sp.add_parser("completar", help="Escribe el JSON del agente en el libro y devuelve los resultados")
    cp_.add_argument("xlsx")
    cp_.add_argument("json")

    p = sp.add_parser("precio")
    p.add_argument("tickers", nargs="+")

    m = sp.add_parser("semaforo")
    m.add_argument("--precio", type=float, required=True)
    m.add_argument("--entrada", type=float, required=True)
    m.add_argument("--justo", type=float, required=True)
    m.add_argument("--cartera", type=float)

    sp.add_parser("macro")
    sp.add_parser("llamadas")

    a = ap.parse_args(argv)
    if a.cmd == "screen":
        from . import screener
        r = screener.ejecutar(top=a.top, con_precios=not a.sin_precios, refrescar=a.refrescar, hilos=a.hilos,
                              solo=a.solo.split(",") if a.solo else None)
        print(screener.a_markdown(r))
        print(f"Guardado en data/screens/{r['fecha']}.md y .json")
    elif a.cmd == "ficha":
        from . import ficha
        pm = None
        if a.precio is not None:
            pm = {"precio": a.precio, "fecha": a.fecha_precio, "fuente": a.fuente_precio, "verificado": True}
        hist = ficha.cargar_historico(a.historico) if a.historico else None
        r = ficha.construir(a.ticker, a.cartera, a.fx, a.adr, a.fcf, a.refrescar, pm, hist, av_income=a.av_income)
        print(ficha.resumen_texto(r))
        print(f"\nFicha completa: analisis/{r['ticker']}/{r['fecha']}-ficha.json")
    elif a.cmd == "rubrica":
        from datetime import date

        from . import ficha, rubrica
        from .screener import criterios
        t = a.ticker.upper()
        salida = a.out or str(red.RAIZ / "analisis" / t / f"{date.today().isoformat()}-rubrica.xlsx")
        (red.RAIZ / "analisis" / t).mkdir(parents=True, exist_ok=True)
        hist = dict(ficha.cargar_historico(a.historico)) if a.historico else {}
        rf = _seguro(fred.tasa_libre_riesgo)
        wacc = None if "error" in rf else valuacion.wacc(rf["valor"], prima_mercado=criterios()["valoracion"]["prima_mercado"])
        ntm = None
        if a.ingresos_ntm:
            ntm = {"ingresos": a.ingresos_ntm, "eps": a.eps_ntm, "etiqueta": a.etiqueta_ntm}
        pp = {}
        if a.precios_peers:
            for par in a.precios_peers.split(","):
                k, v = par.split("=")
                pp[k.strip().upper()] = float(v)
        _imprimir(rubrica.generar(t, salida, a.precio, wacc, hist, ntm,
                                  a.peers.split(",") if a.peers else None, pp))
    elif a.cmd == "completar":
        from . import rubrica
        _imprimir(rubrica.completar(a.xlsx, a.json))
    elif a.cmd == "precio":
        _imprimir({t: _seguro(precios.precio, t) for t in a.tickers})
    elif a.cmd == "semaforo":
        r = {"semaforo": valuacion.semaforo(a.precio, a.entrada, a.justo)}
        if a.cartera:
            r.update(valuacion.tramos(a.cartera))
        _imprimir(r)
    elif a.cmd == "macro":
        _imprimir({"tasa_10a": _seguro(fred.tasa_libre_riesgo), "sp500": _seguro(fred.sp500)})
    elif a.cmd == "llamadas":
        _imprimir(red._contador())
    return 0


def _seguro(fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


if __name__ == "__main__":
    sys.exit(main())
