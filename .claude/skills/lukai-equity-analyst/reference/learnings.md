# Lecciones acumuladas (LukAI)
Una línea por lección: `- AAAA-MM-DD [TICKER] lección`. Máx. 3 líneas por análisis; sin duplicar lo ya escrito en SKILL.md ("Lecciones de ejecución"). Mantener corto: se lee en cada análisis.

- 2026-11-06 [NVDA] Las lineas "EBIT"/"EBITDA" anuales de yfinance incluyen ganancias NO operativas de inversiones; usa Operating Income (+D&A) para EBIT/EBITDA fila 7-8 o el ROIC/EV se distorsiona.
- 2026-11-06 [NVDA] yfinance info["forwardEps"] suele ser el estimado +1y (2 anos fuera), no NTM; usa t.earnings_estimate filas 0y/+1y y mezcla conservador. "Diluted EPS" puede venir 0.0 -> calcula NI/acciones.
- 2026-11-06 [NVDA] TTM de acciones: NO sumes los 4 trimestres de "Diluted Average Shares" (da ~4x); usa el nivel del ultimo trimestre.

- 2026-11-07 [NVDA] Con años fiscales desfasados (FY termina en enero), Alpha Vantage EARNINGS_ESTIMATES trae el FY en curso y el siguiente; NTM conservador = FY en curso. Anota cuál usaste en la etiqueta NTM.
- 2026-11-07 [SKILL] build_rubrica --blank dejaba Cualitativo en 5/5 y comparables de ejemplo: corregido en v1.3. Un criterio sin evaluar ahora suma 0, no el máximo.
- 2026-11-07 [NVDA] Antes de fiarte del EPS GAAP (ancla P/E), compara "Other income, net" con el resultado antes de impuestos en el 10-Q: en NVDA fue 17% en 1S FY27 (ganancias no realizadas de participaciones). Va en K5 como "vigilar" y refuerza usar el FCF.
- 2026-11-07 [SKILL] Forward de peers (Comparables C5/C13): FY en curso de AV EARNINGS_ESTIMATES (aunque haya cerrado sin reportar) sobre la base del último 10-K; documenta FY, base y precio en F13.
- 2026-11-07 [ENTORNO] nvidianews/investor.nvidia.com dan 403 en el proxy; la fecha de resultados sale con 1 WebSearch del comunicado "Sets Conference Call".
- 2026-11-10 [META] Con capex en expansión, lee en el 10-Q la nota de compromisos (arrendamientos no iniciados, VIE de data centers con garantías de valor residual) y los 8-K de financiación posteriores al 10-Q (bonos, convertibles, ventas a plazo): cambian K5 y la deuda más que el balance.
- 2026-11-10 [META] Para forward de peers, usa el mismo FY que el NTM del analizado; si su EPS FY+1 < FY en curso (ganancias no operativas), anota ambos P/E en F13 como "verificar".
- 2026-11-10 [META] La caída del EPS estimado suele salir de cargos discretos (impuestos, litigios): búscalos en el Ex. 99.1 del 8-K de resultados ("excluding this charge") antes de leer el 10-Q completo.
