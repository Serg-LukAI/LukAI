"""Tests sin red: python -m unittest discover -s tests"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("LUKAI_CACHE", tempfile.mkdtemp(prefix="lukai-test-"))

from lukai import edgar, metricas, precios, red, valuacion  # noqa: E402


def _hecho(start, end, val, form="10-K", filed=None, accn="0000-00-1"):
    h = {"end": end, "val": val, "form": form, "filed": filed or end, "accn": accn}
    if start:
        h["start"] = start
    return h


def companyfacts_sintetico():
    """Empresa ficticia: 5 años, crece 20%/año, split 10:1 en el 4.º año, con un 10-Q posterior."""
    anios = [("2020-01-01", "2020-12-31"), ("2021-01-01", "2021-12-31"), ("2022-01-01", "2022-12-31"),
             ("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31")]
    ingresos = [100, 120, 144, 172.8, 207.36]
    eps = [10.0, 12.0, 14.4, 1.728, 2.0736]          # split 10:1 entre 2022 y 2023, EPS sin ajustar
    acciones = [10, 10, 10, 100, 100]
    gaap = {
        "Revenues": {"units": {"USD": [_hecho(s, e, v * 1e6) for (s, e), v in zip(anios, ingresos)] + [
            _hecho("2025-01-01", "2025-06-30", 120e6, form="10-Q", accn="q2-2025"),
            _hecho("2024-01-01", "2024-06-30", 100e6, form="10-Q", accn="q2-2025")]}},
        "GrossProfit": {"units": {"USD": [_hecho(s, e, v * 0.6e6) for (s, e), v in zip(anios, ingresos)]}},
        "OperatingIncomeLoss": {"units": {"USD": [_hecho(s, e, v * 0.3e6) for (s, e), v in zip(anios, ingresos)]}},
        "NetIncomeLoss": {"units": {"USD": [_hecho(s, e, v * 0.2e6) for (s, e), v in zip(anios, ingresos)]}},
        "EarningsPerShareDiluted": {"units": {
            "pure": [],
            "USD/shares": [_hecho(s, e, v) for (s, e), v in zip(anios, eps)]}},
        "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [
            _hecho(s, e, v * 1e6) for (s, e), v in zip(anios, acciones)]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            _hecho(s, e, v * 0.25e6) for (s, e), v in zip(anios, ingresos)]}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [
            _hecho(s, e, v * 0.05e6) for (s, e), v in zip(anios, ingresos)]}},
        "StockholdersEquity": {"units": {"USD": [_hecho(None, e, 150e6) for _, e in anios]}},
        "LongTermDebt": {"units": {"USD": [_hecho(None, e, 20e6) for _, e in anios]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_hecho(None, e, 30e6) for _, e in anios]}},
        "DepreciationDepletionAndAmortization": {"units": {"USD": [_hecho(s, e, 5e6) for s, e in anios]}},
        "OperatingLeaseLiability": {"units": {"USD": [_hecho(None, e, 40e6) for _, e in anios] + [
            _hecho(None, "2025-06-30", 45e6, form="10-Q", accn="q2-2025")]}},
    }
    return {"facts": {"us-gaap": gaap}}


class TestEdgarYMetricas(unittest.TestCase):
    def setUp(self):
        self.series = edgar.series_anuales(companyfacts_sintetico())
        self.filas = metricas.anuales(self.series)

    def test_series_alineadas_y_unidad_correcta(self):
        self.assertEqual(len(self.series["cierres"]), 5)
        self.assertEqual(self.series["moneda"], "USD")
        # La unidad 'pure' vacía no debe ocultar el EPS en 'USD/shares'.
        self.assertTrue(all(f["eps"] is not None for f in self.filas))

    def test_ajuste_por_split(self):
        self.assertAlmostEqual(self.filas[0]["eps"], 1.0)        # 10.0 / 10
        self.assertAlmostEqual(self.filas[0]["acciones"], 100e6)
        r = metricas.resumen(self.filas)
        self.assertAlmostEqual(r["cagr_eps"], 0.20, places=3)
        self.assertAlmostEqual(r["cagr_ingresos"], 0.20, places=3)

    def test_knockouts_y_puntaje(self):
        cfg = {"anios_minimos": 4, "cagr_ingresos_3a_min": 0, "cagr_eps_3a_min": 0, "anios_caida_margen_max": 3,
               "wacc_proxy": 0.09, "deuda_neta_ebitda_max": 3.5}
        r = metricas.resumen(self.filas)
        self.assertEqual(metricas.knockouts(r, cfg), [])
        decreciente = dict(r, cagr_ingresos_3a=-0.05)
        self.assertTrue(any("Ingresos en caída" in k for k in metricas.knockouts(decreciente, cfg)))
        pts = metricas.puntaje_calidad(r, {"roic_ideal": .15, "roic_aceptable": .12, "crec_ideal": .12,
                                           "crec_aceptable": .08, "margen_bruto_ideal": .5,
                                           "margen_bruto_aceptable": .3})
        self.assertGreaterEqual(pts["total"], 90)

    def test_ttm(self):
        valor_fy = self.series["conceptos"]["ingresos"]["2024-12-31"]["valor"]
        t = edgar.ttm(companyfacts_sintetico(), "ingresos", "2024-12-31", valor_fy)
        self.assertAlmostEqual(t["valor"], valor_fy + 20e6)
        self.assertEqual(t["hasta"], "2025-06-30")

    def test_eps_ausente_usa_utilidad_neta(self):
        filas = [dict(f, eps=None) for f in self.filas]
        r = metricas.resumen(filas)
        self.assertIn("utilidad neta", r["eps_fuente"])
        self.assertAlmostEqual(r["cagr_eps"], 0.20, places=3)


    def test_roic_incluye_arrendamientos(self):
        f = self.filas[-1]
        self.assertEqual(f["arrendamientos"], 40e6)
        # capital invertido = patrimonio + deuda − caja + arrendamientos = 150 + 20 − 30 + 40
        self.assertAlmostEqual(f["capital_invertido"], 180e6)
        self.assertEqual(f["deuda"], 20e6)  # los arrendamientos NO son deuda financiera

    def test_ultimo_saldo_trimestral(self):
        s = edgar.ultimo_saldo(companyfacts_sintetico(), "arrendamientos")
        self.assertEqual((s["valor"], s["hasta"]), (45e6, "2025-06-30"))


class TestPuenteRubrica(unittest.TestCase):
    def test_valores_datos_desde_edgar(self):
        from lukai import rubrica
        with mock.patch.object(edgar, "cik_de", return_value=1), \
             mock.patch.object(edgar, "hechos", return_value=companyfacts_sintetico()):
            v, brechas = rubrica.valores_datos("XYZ", 50.0, 0.1, {"2024-12-31": 40.0}, None)
        d = v["Datos"]
        self.assertEqual([d["B4"], d["E4"], d["F4"]], ["FY2021", "FY2024", "TTM 2025-06-30"])
        self.assertEqual(d["E5"], 207.4)            # millones
        self.assertEqual(d["F5"], 227.4)            # TTM = FY + YTD − YTD previo
        self.assertEqual(d["E21"], 40.0)            # arrendamientos fuera de la deuda (fila 21)
        self.assertEqual(d["F21"], 45.0)            # saldo del último trimestre
        self.assertEqual(d["E16"], 20.0)
        self.assertEqual(d["E20"], 40.0)            # precio de cierre fiscal
        self.assertEqual(d["B23"], 50.0)
        self.assertIn("accn", d["H5"])
        self.assertTrue(any("NTM" in b for b in brechas))


class TestValuacion(unittest.TestCase):
    def test_reverse_dcf_recupera_crecimiento(self):
        ve = valuacion.valor_presente(100, 0.12, 0.10)
        self.assertAlmostEqual(valuacion.reverse_dcf(ve, 100, 0.10), 0.12, places=4)

    def test_semaforo_y_tramos_como_en_el_sheet(self):
        # Valores de la pestaña Watchlist (NVDA, 06/11/2026).
        self.assertEqual(valuacion.semaforo(186.64, 178.11, 209.54), "AMARILLO")
        self.assertEqual(valuacion.semaforo(170, 178.11, 209.54), "VERDE")
        self.assertEqual(valuacion.semaforo(215, 178.11, 209.54), "ROJO")
        self.assertEqual(valuacion.tramos(61747), {"techo": 3087, "tramos": [1235, 926, 926]})
        self.assertAlmostEqual(valuacion.precio_entrada(209.54, 0.15), 178.11, places=2)

    def test_crecimiento_conservador(self):
        self.assertAlmostEqual(valuacion.crecimiento_conservador([0.3, 0.16, None]), 0.12)
        self.assertEqual(valuacion.crecimiento_conservador([0.9]), 0.20)  # tope


class TestFuentes(unittest.TestCase):
    def test_fallback_a_yahoo_queda_marcado(self):
        falla = mock.Mock(side_effect=precios.SinDato("caída simulada"))
        yahoo = mock.Mock(return_value={"precio": 100.0, "fecha": "2026-11-06", "fuente": "Yahoo (no oficial)"})
        with mock.patch.object(precios, "RUTAS", [("Alpha Vantage", falla), ("Stooq", falla), ("Yahoo", yahoo)]):
            p = precios.precio("XYZ")
        self.assertEqual(p["precio"], 100.0)
        self.assertFalse(p["verificado"])
        self.assertEqual(len(p["errores_previos"]), 2)

    def test_ruta_principal_verificada(self):
        av = mock.Mock(return_value={"precio": 50.0, "fecha": "2026-11-06", "fuente": "Alpha Vantage"})
        with mock.patch.object(precios, "RUTAS", [("Alpha Vantage", av)]):
            self.assertTrue(precios.precio("XYZ")["verificado"])

    def test_cache_evita_segunda_llamada(self):
        resp = mock.Mock(content=b'{"ok": 1}', text='{"ok": 1}')
        resp.raise_for_status = mock.Mock()
        with mock.patch.object(red.requests, "get", return_value=resp) as get:
            url = "https://data.sec.gov/prueba-cache.json"
            self.assertEqual(red.obtener_json(url, 1), {"ok": 1})
            self.assertEqual(red.obtener_json(url, 1), {"ok": 1})
            self.assertEqual(get.call_count, 1)

    def test_cupo_agotado(self):
        with mock.patch.object(red, "llamadas_hoy", return_value=999):
            with self.assertRaises(red.CupoAgotado):
                red.obtener("https://www.alphavantage.co/query?x=sin-cache", 0)


if __name__ == "__main__":
    unittest.main()
