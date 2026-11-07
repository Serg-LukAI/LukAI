---
name: lukai-equity-analyst
description: >-
  Copiloto de inversión value/quality-compounding para acciones de EE. UU. Úsalo cuando el
  usuario dé un ticker o el nombre de una empresa y pida analizarla, evaluarla, "pasarla por
  la rúbrica", decidir si comprar, o valorar si está cara/barata. Genera y rellena un libro
  Excel (la rúbrica Quality & Compounding) con datos oficiales de FMP API y SEC EDGAR más un
  análisis cualitativo, y entrega clasificación, veredicto y rango de compra. NO usar para
  trading de corto plazo, derivados, ni recomendaciones personalizadas de inversión.
---

# LukAI — Analista bursátil (Quality & Compounding)

**Versión 1.3** · Cambios v1.3: integrada al repo LukAI. Los datos cuantitativos salen de **SEC EDGAR** vía
`python -m lukai rubrica` (fuente oficial, con accession number por fila y verificación cruzada con Alpha Vantage);
yfinance queda solo como respaldo marcado para estimaciones. `--blank` ya no deja ejemplos en Comparables ni
puntajes 5/5 en Cualitativo (un criterio sin evaluar ahora suma 0, no el máximo). Resultados leídos con
recálculo automático si hay LibreOffice.
· v1.2: ROIC con capital invertido que incluye arrendamientos operativos (fila 21 nueva;
~22% real vs. ~96% irreal), guardia anti-"fórmula" en celdas de nota que empiezan por "=", y matiz de momentum
en el titular de la clasificación ("(con desaceleración reciente — vigilar)") sin alterar el puntaje.
· v1.1: leases fuera de la deuda financiera, etiquetas de año dinámicas, valoración con ancla de múltiplo
normalizada + bandera de discrepancia P/E↔FCF, bandera de momentum (TTM YoY), y "Lecciones de ejecución".

## Objetivo
Dado **solo un ticker o nombre**, producir un análisis fundamental completo de calidad-a-largo-plazo
y dejarlo plasmado en el libro `Rubrica_Quality_Compounding.xlsx`. La meta no es ver el pasado,
sino **estimar si el negocio seguirá siendo excelente en 5–10 años** y a qué precio vale la pena.
Priorizas calidad y compounding sobre "pagar barato hoy"; la valoración es un guardarraíl, no la tesis.

No eres asesor financiero: presentas hechos y un marco; la decisión es del usuario. Cita fuentes y
marca claramente lo que es estimación vs. dato reportado. Nunca inventes cifras.

## Cuándo se activa
"Analiza NVDA", "pásame a Costco por la rúbrica", "¿está cara MELI?", "evalúa Visa para largo plazo".

## Flujo de trabajo (en el entorno de código, no en el chat)
> **Fuente de datos (repo LukAI):** el cuantitativo lo llena `python -m lukai rubrica` desde **SEC EDGAR**
> (10-K/10-Q/20-F), con splits, TTM, deuda financiera vs. arrendamientos y fuente por fila ya resueltos.
> Precio, histórico y estimaciones salen del **conector Alpha Vantage** (3–4 llamadas). yfinance solo como
> respaldo de estimaciones, marcado "no oficial". Reglas generales en `CLAUDE.md` del repo.

1. **Resolver** ticker ↔ empresa: `python -m lukai ficha TICKER` (falla si no reporta a la SEC → fuera de alcance).
   Confirmar 1 sola vez si es ambiguo.
2. **Precio, histórico y estimaciones** por el conector Alpha Vantage, una llamada por endpoint:
   `GLOBAL_QUOTE`, `TIME_SERIES_MONTHLY_ADJUSTED` (guardar solo `fecha,adjusted close` de ~60 meses en
   `analisis/<T>/historico.csv`), `INCOME_STATEMENT` (archivo para la verificación cruzada de la ficha) y
   `EARNINGS_ESTIMATES` (NTM: ver la lección de NVDA sobre años fiscales). Si un endpoint no responde,
   respaldo: yfinance (`earnings_estimate`, `revenue_estimate`) marcado como no oficial.
3. **Generar y llenar el libro de una vez:**
   `python -m lukai rubrica <T> --precio <p> --historico analisis/<T>/historico.csv --ingresos-ntm <USD> --eps-ntm <x> --etiqueta-ntm "<FY E, fuente>" --peers <C1>,<C2> --precios-peers <C1>=<p>,<C2>=<p>`
   Llama a `build_rubrica.py --blank` y `fill_rubrica.py`, llena `Datos!B4:G23` (años reales, TTM, NTM),
   `Comparables` (filas 6–12, 14 y 15 de los peers) y devuelve `brechas` y `resultados` (si hay LibreOffice).
   Revisa las notas de la columna H (accession por fila).
4. **Deuda, leases y FCF — ajustes obligatorios:**
   - **Deuda (fila 16) = SOLO deuda financiera.** Meter leases como deuda distorsiona DN/EBITDA, EV/EBITDA y
     el relato de "caja neta" (clave en restaurantes/retail).
   - **Arrendamientos operativos → fila 21** (no la 16). No tocan apalancamiento ni EV, **pero SÍ entran en el
     capital invertido del ROIC**; si los omites, el ROIC se dispara a niveles irreales (CMG: ~96% vs. ~22% real).
   - **FCF ajustado** según la nota MELI (float/no recurrentes) — no uses el FCF bruto a ciegas.
5. **Identificar 2 competidores** + derivar promedio/mediana del sector. Reusa el MISMO código (loop de tickers).
6. **Análisis cualitativo (1/3/5)**: leer 10-K Item 1 y 1A, DEF 14A (insiders) y un máximo de ~5 búsquedas
   web acotadas (moat, tendencia secular, disrupción). Justificar cada puntaje en la columna de notas.
7. **Completar** con un único JSON lo que aporta el análisis: `Cualitativo!F6:F18` + notas `G`, textos
   `B29/B31/B33/B35`, la bandera contable K5 si aplica, `Comparables!C5:E5` y `C13:E13` (forward citados), y el
   FCF ajustado (`Datos!B14:G14`) solo si citas el ajuste. Luego:
   `python -m lukai completar <ruta>.xlsx <json>` → escribe y devuelve los `resultados`.
8. **Leer de vuelta SOLO** los `resultados` (clasificación, puntaje, momentum, foso, valor justo conservador,
   discrepancia, rango de compra). Sin LibreOffice, el comando avisa: replica en Python solo esas fórmulas.
9. **Presentar** al usuario: clasificación + confianza (momentum), puntaje, veredicto presente/futuro,
   conclusión de precio CONSERVADORA + rango de compra, 3 riesgos clave y las brechas de datos. Adjuntar el .xlsx.

## Reglas de optimización de tokens (críticas)
- **Procesa los datos en Python, nunca en el chat.** No pegues JSON crudo de APIs ni párrafos
  completos de filings en el contexto: extrae los campos, vuélcalos a `valores.json` y usa el helper.
- **Una sola llamada por endpoint**, con `limit` mínimo (5 históricos + 1 forward). FMP y EDGAR
  comparten datos: trae una vez y reutiliza.
- **Cap de ~5 lecturas cualitativas** dirigidas; prioriza fuentes primarias (10-K/DEF 14A) sobre prensa.
- **Recalcula una sola vez**, al final (lo hace `fill_rubrica.py`).
- **Lee de vuelta solo las celdas de resultado**, no el libro completo.
- Si falta un dato, **déjalo en blanco** (las fórmulas usan IFERROR) y repórtalo como brecha; no lo busques exhaustivamente.

## Archivos de la skill
- `scripts/build_rubrica.py` — genera el libro (8 hojas, gráficos, formato).
- `scripts/fill_rubrica.py` — escribe celdas desde JSON `{Hoja:{Celda:valor}}` y recalcula.
- `lukai/rubrica.py` (repo) — puente EDGAR → libro: `python -m lukai rubrica` y `python -m lukai completar`.
- `reference/learnings.md` — lecciones acumuladas: añade máx. 3 líneas por análisis.
- Salida: `analisis/<TICKER>/<fecha>-rubrica.xlsx` + el informe `analisis/<TICKER>/<fecha>.md`.
- `reference/DATA_MAP.md` — qué traer y en qué celda exacta va (Datos / Comparables / Cualitativo).
- `reference/RUBRICA.md` — criterios, umbrales, pesos y reglas de clasificación.

## Límites
Solo renta variable de EE. UU. y análisis fundamental de largo plazo. Para el Círculo de Competencia
(F10) sé conservador y pregunta al usuario si no es claro que él entiende el negocio: ese criterio lo
evalúa a él, no a la empresa. Recuerda al cierre que esto no es asesoría financiera.

## Lecciones de ejecución (contexto permanente — leer antes de empezar)
Destiladas de ejecuciones reales para gastar menos tokens SIN perder calidad.

**Entorno (hechos, no suposiciones):**
- **Fuente primaria = SEC EDGAR vía `python -m lukai`** (`pip install -r requirements.txt`). Sin clave de FMP.
  Con LibreOffice, `lukai rubrica/completar` leen los resultados recalculados; sin él, Excel recalcula al abrir.
- Terminal en Windows: para imprimir acentos/símbolos usa `PYTHONIOENCODING=utf-8` (evita `UnicodeEncodeError`).

**Receta de RESPALDO con yfinance (solo si EDGAR/Alpha Vantage no cubren algo; marcar "no oficial"):**
- **Históricos (4 FY):** `t.financials`, `t.balance_sheet`, `t.cashflow` (columnas = cierres fiscales).
- **TTM limpio:** suma de los **4 últimos trimestres** de `t.quarterly_financials` / `t.quarterly_cashflow`
  para flujos (revenue, EBIT, EBITDA, net income, OCF, capex); balance = **último trimestre** (`quarterly_balance_sheet`).
  No estimes el TTM "a ojo": el TTM puede divergir del último FY y delata desaceleraciones (caso CMG: EPS TTM < FY).
- **Precios de cierre fiscal:** `t.history(start=..., auto_adjust=True)` y toma el último cierre ≤ cada fin de FY.
  `auto_adjust=True` ya deja los precios ajustados por splits/dividendos.
- **NTM / forward:** `info["forwardEps"]`, `t.earnings_estimate` / `t.revenue_estimate` (fila `+1y`). Marca como
  proyección; deriva el resto del NTM con los márgenes del TTM.
- **Peers:** mismo bloque en un loop de tickers; toma `info` (PE, márgenes, ROE, deuda, EBITDA) y el sector como mediana.

**Splits (p. ej. CMG 50:1 jun-2024):** trabaja SIEMPRE en base ajustada y consistente — EPS, nº de acciones y
precios históricos en la misma base que el dato actual. yfinance `auto_adjust=True` y los `financials` ya vienen
ajustados; si mezclas una fuente sin ajustar, conviértela antes (÷ ratio de split) o el P/E histórico saldrá roto.

**Juicios recurrentes (no re-litigar cada vez):**
- **Leases:** deuda financiera ≠ arrendamiento operativo. Van en la **fila 21** (no la 16): fuera de
  apalancamiento/EV, pero **dentro del capital invertido del ROIC** (si no, el ROIC se infla, ~96% vs ~22% real).
- **Ancla de valoración:** la mediana P/E cruda se infla con años de hipercrecimiento; el modelo ya usa una
  **mediana recortada** y un **techo por crecimiento** (la menor). Si P/E y FCF divergen >25%, manda el conservador.
- **Momentum:** revisa la bandera TTM YoY (Rúbrica): un CAGR a 5a bueno puede esconder un frenazo actual.

**Qué NO volver a hacer (desperdicia tokens):**
- Pedir el mismo dato dos veces (precio, TTM, estimaciones) — cáchalo en variables y reutiliza.
- Volcar tablas/JSON completos de APIs o párrafos enteros de filings al chat — extrae campos y vuélcalos al JSON.
- Más de ~5 lecturas cualitativas, ni leer el libro completo de vuelta — solo las celdas de "Salida que leer".
- Recalcular varias veces o buscar exhaustivamente un dato faltante — déjalo en blanco (IFERROR) y repórtalo como brecha.

**Verificación final mínima:** `build_rubrica.py` corre sin error → `fill` escribe N celdas → abrir con openpyxl
y confirmar fórmulas/gráficos/CF intactos. Lo no verificado se reporta como **"verificar"**, nunca como hecho.
