# DATA_MAP — Qué traer y exactamente dónde ponerlo

Todas las cifras monetarias en **millones (mm)**. La columna por período en la hoja `Datos`:
`B = FY-4 · C = FY-3 · D = FY-2 · E = FY-1 (último fiscal) · F = TTM · G = NTM (proyección a 1 año)`.

> **Fuente en este entorno:** sin clave de FMP → usa **yfinance** (las columnas "FMP →" de abajo son el
> mapeo conceptual; el campo equivalente de yfinance está en la receta de SKILL.md → "Lecciones de ejecución").
>
> **Etiquetas de año DINÁMICAS (obligatorio):** los encabezados `Datos!B4:G4` ya NO son fijos. El JSON de
> rellenado **debe** sobreescribirlos con los años fiscales reales cargados (4 históricos + TTM + NTM),
> p. ej. `{"Datos": {"B4":"FY2022", ..., "F4":"TTM 2026", "G4":"NTM 2026E"}}`. Alternativa al generar:
> `build_rubrica.py --years "FY2022,FY2023,FY2024,FY2025,TTM 2026,NTM 2026E"`. Nunca dejes los placeholders
> `FY-4…NTM` ni un año fijo que quede desfasado.

## Hoja `Datos` — fila por métrica (col A) y origen sugerido

| Fila | Métrica | FMP (endpoint → campo) | EDGAR / verificación |
|------|---------|------------------------|----------------------|
| 5  | Ingresos ($mm) | income-statement → `revenue` | 10-K Income Statement |
| 6  | Utilidad bruta ($mm) | income-statement → `grossProfit` | — |
| 7  | EBITDA ($mm) | income-statement → `ebitda` (o `operatingIncome`+`depreciationAndAmortization`) | — |
| 8  | EBIT ($mm) | income-statement → `operatingIncome` | — |
| 9  | Utilidad neta ($mm) | income-statement → `netIncome` | — |
| 10 | EPS diluido ($) | income-statement → `epsdiluted` | — |
| 11 | Acciones diluidas (mm) | income-statement → `weightedAverageShsOutDil` | — |
| 12 | Flujo de caja operativo ($mm) | cash-flow-statement → `operatingCashFlow` | Cash Flow Statement |
| 13 | Capex ($mm) | cash-flow-statement → `capitalExpenditure` (valor absoluto) | — |
| 14 | **FCF ajustado ($mm)** | OCF − \|Capex\|; **ajustar** (ver nota FCF abajo) | press release / 10-K MD&A |
| 15 | Caja e inversiones ($mm) | balance-sheet → `cashAndShortTermInvestments` | Balance Sheet |
| 16 | Deuda total ($mm) — **SOLO deuda financiera** | balance-sheet → `totalDebt` **menos** arrendamientos operativos | ver nota Leases abajo |
| 17 | Patrimonio ($mm) | balance-sheet → `totalStockholdersEquity` | — |
| 18 | Activos totales ($mm) | balance-sheet → `totalAssets` | — |
| 19 | Tasa impositiva efectiva | ratios → `effectiveTaxRate` (o `incomeTaxExpense`/`incomeBeforeTax`) | — |
| 20 | Precio acción del período ($) | columnas B–E: precio de cierre fiscal (quote/historical). F y G se autollenan con B23 | — |
| 21 | **Arrendamientos operativos ($mm)** | pasivo por arrendamiento operativo / activo ROU (no es deuda financiera) | 10-K nota de Leases |
| 22 | WACC estimado | estimación propia (CAPM aprox.) o `wacc` de proveedor | — |
| 23 | **Precio actual ($)** | quote → `price` | — |

**Columna F (TTM):** usa los últimos 4 trimestres (sumar income/cash-flow trimestrales; balance = último trimestre). Si no hay TTM fácil, usa el último FY y anótalo.
**Columna G (NTM):** analyst-estimates → `estimatedRevenueAvg`, `estimatedEpsAvg` del próximo año; deriva el resto con los márgenes del TTM si no hay estimado directo. Marca claramente que es proyección.

### Nota FCF ajustado (lección MELI)
El FCF GAAP puede inflarse por el **float** (depósitos de clientes / fintech) u otras partidas no recurrentes. Cuando el negocio tenga float, tarjetas, o financiación al consumo (p. ej. Mercado Pago en MELI, donde el FCF GAAP llegó a ~7x el ajustado), **usa el FCF ajustado que reporta la empresa** en su release/MD&A, no `freeCashFlow` de FMP. Documenta el ajuste en la columna H.

### Nota Leases — filas 16 y 21, y ROIC (lección CMG)
El `totalDebt` de los proveedores (FMP/yfinance) suele **incluir pasivos por arrendamiento operativo** (ASC 842).
Para **restaurantes, retail y cualquier negocio con muchos leases**, esos arrendamientos NO son deuda financiera:
incluirlos distorsiona **Deuda neta/EBITDA**, **EV/EBITDA** y el relato de **"caja neta"** (caso CMG: ~$5.1B de
"deuda" eran leases; ex-leases la empresa tiene caja neta).

Regla en dos filas (separa apalancamiento de capital invertido):
- **Fila 16 = solo deuda financiera** (préstamos, bonos, leasing financiero). Alimenta DN/EBITDA, EV/EBITDA y K4.
- **Fila 21 = arrendamientos operativos** (pasivo ROU). NO toca apalancamiento ni EV, **pero SÍ se suma al
  capital invertido del ROIC** (`Ratios!ROIC = EBIT·(1−t) / (deuda financiera + patrimonio − caja + leases)`).

Por qué: los leases financian activos operativos reales (locales). Si los sacas del denominador del ROIC, el
ROIC se dispara a niveles irreales (caso CMG: **~96% sin leases vs. ~22% con leases** en el capital). Pon la fila 21
en 0 si el negocio casi no usa arrendamientos. Documenta el monto en la columna H de la fila 16 o 21.

## Hoja `Comparables` — columnas C (Competidor 1), D (Competidor 2), E (Promedio sector)
Mismas métricas, fila por fila (TTM salvo donde diga forward). Reusa el MISMO código para los 2 peers (loop de tickers) y deriva el sector como **mediana del sub-sector** (peers + la empresa) o usa medianas sectoriales si las tienes.

| Fila | Métrica | Fuente |
|------|---------|--------|
| 5 Crec. ingresos NTM | analyst-estimates | 6 CAGR EPS 5a (calc.) | 7 Margen bruto | 8 Margen EBITDA |
| 9 ROE | 10 ROIC | 11 Deuda neta/EBITDA | 12 P/E TTM | 13 P/E fwd | 14 EV/EBITDA TTM | 15 FCF yield |

(La columna B = Empresa X se autocalcula; no la toques.)

## Hoja `Cualitativo` — puntajes 1 / 3 / 5 (col F) + notas (col G)
NO viene de números: viene de **lectura cualitativa** de fuentes oficiales. Asigna 1/3/5 según los anclajes que ya trae cada fila y **justifica en la columna G con la fuente**.

| Celda | Criterio | Dónde leer |
|-------|----------|-----------|
| F6  | Naturaleza del negocio | 10-K Item 1 (Business); modelo de ingresos |
| F7  | Foso competitivo (moat) | 10-K Item 1/1A; cuota de mercado; estructura competitiva |
| F8  | Poder de precios | tendencia de márgenes brutos; comentarios de pricing en earnings call |
| F9  | Calidad directiva | DEF 14A (propiedad de insiders, compensación); historial de asignación de capital |
| F10 | Círculo de competencia | autoevaluación del usuario — **si no es claro, marca conservador (1–3) y pregunta** |
| F14 | Trayectoria del moat | 1A Risk Factors; dinámica competitiva; inversión en I+D/red |
| F15 | Pista de reinversión (TAM) | MD&A; TAM declarado; ROIC incremental |
| F16 | Vientos seculares | tendencia estructural de la industria (búsqueda web acotada) |
| F17 | **Riesgo de disrupción** (5 = riesgo BAJO) | 1A Risk Factors; amenazas tecnológicas/IA/regulatorias |
| F18 | Opcionalidad | nuevas líneas/segmentos; pipeline; ópticas de expansión |

Texto libre: `B29` tesis · `B31` riesgos · `B33` señales de venta · `B35` catalizadores.

## Salida que SÍ debes leer de vuelta (no leas todo el libro)
> Sin LibreOffice no hay recálculo automático: **replica estas fórmulas en Python** para reportar los números
> exactos. El usuario verá los valores cuando abra el .xlsx en Excel.
- `Rúbrica!B33` (puntaje), `Rúbrica!B35` (clasificación)
- `Rúbrica!B41` (**bandera de momentum** TTM YoY), `Rúbrica!B42` (**confianza** de la clasificación)
- `Cualitativo!B25` (¿el foso se fortalece/erosiona?), `Cualitativo!B26` (veredicto)
- `Valoración!B12` (**ancla de múltiplo normalizada**), `Valoración!B30` (**valor justo conservador / titular**)
- `Valoración!B29` (**bandera de discrepancia** P/E↔FCF), `Valoración!B33` (barato/razonable/caro), `B35:B36` (rango de compra)
- Celdas que quedaron en blanco → repórtalas como brechas de datos.
