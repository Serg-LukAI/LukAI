# LukAI Inversor

Herramienta personal de Sergio para invertir con proceso: **screener → watchlist → análisis profundo → registro mensual**.
Sergio es inversor value de largo plazo, nivel intermedio: entiende valoración y estados financieros, y le preocupan
las alucinaciones. Prioriza veracidad y respaldo sobre velocidad. Responde siempre en español, claro y breve.

## Comandos

| Comando | Cuándo | Qué hace |
|---|---|---|
| `/screener` | 1 vez por trimestre | Filtra el universo con datos de EDGAR y propone hasta 10 candidatos para la Watchlist |
| `/analizar TICKER` | 1–2 empresas por trimestre | Rúbrica completa + valoración + abogado del diablo → veredicto y precio de entrada |
| `/cierre-mes` | Último día del mes | Registra saldos y movimientos en el Sheet, actualiza semáforos y revisa decisiones pasadas |

## Reglas no negociables

1. **Proponer, nunca ejecutar.** Ningún agente da órdenes de compra/venta ni toca brokers. Sergio decide.
2. **Ninguna cifra sin fuente.** Todo número sale de `python -m lukai ...` (EDGAR, FRED) o del conector Alpha Vantage,
   con su filing o fecha. Si falta un dato: escribir **"sin dato"**, nunca estimarlo en silencio. Nunca calcular
   ratios "de memoria": usar la ficha.
3. **Reglas del Plan (pestaña Plan del Sheet):** compra solo el último lunes del mes; tramos 40/30/30 con ≥ 14 días
   entre tramos; máx. 5% por posición; máx. 8 nombres en la Watchlist; vender solo por tesis rota, posición > 8% o
   mejor alternativa; las reglas se cambian solo en la revisión trimestral y por escrito.
4. **Gate de compra:** veredicto *Compounder de Convicción* o *Calidad en Observación* **y** 4 de 5 del checklist
   del satélite. Las **3 líneas de "cómo gana dinero" las escribe Sergio**, nunca el agente.
5. **Escrituras al Sheet:** mostrar primero la propuesta exacta (pestaña, rango, valores) y escribir solo tras un
   "OK" explícito. Nunca escribir en celdas con fórmula ni en las pestañas Resumen o Plan.

## Guardado (obligatorio al final de cada comando)

En sesiones en la nube (celular o web) el contenedor es temporal: **nada queda guardado sin commit y push**.
Al terminar `/screener`, `/analizar` o `/cierre-mes`:
1. Muestra `git status --short` (archivos nuevos o cambiados: `analisis/`, `diario/`, `data/screens/`, `ideas.md`,
   `.claude/skills/lukai-equity-analyst/reference/learnings.md`).
2. Con el OK de Sergio: `git pull --rebase` → commit con un mensaje corto (p. ej. `Análisis NVDA 2026-11-30`) →
   `git push` a la rama por defecto del repositorio (hoy `claude/stock-screener-watchlist-fov7zo`).
3. Si el push falla por conflicto, resuélvelo conservando ambas entradas del diario; nunca uses `--force`.

En el computador de Sergio aplica lo mismo, para que el celular vea el historial.

## Recursos

- Sheet de seguimiento: `Seguimiento inversiones — Sergio`, id `1Cr2R7BfCRsJ6NO0JVd84XCLoFM0SSVbNkdNcMuAvaiY`
  - **Mensual** (fila 3 = encabezados, fila 4 = saldos de partida, una fila nueva por mes). Convenciones de Sergio:
    - A: `=TEXT(DATE(aaaa,m,d),"dd/mm/yyyy")`.
    - B–H (S&P 500, Growth, Emergentes, Acciones ind., Oro, Cripto, Cash): fórmula con la suma por cuenta,
      p. ej. `=11692.8+2017.24` (Hapi + IBKR), para que se vea de dónde sale cada saldo. `-` si es cero.
    - J: aporte neto del mes (`=` suma de aportes − retiros de Movimientos). K: nivel del S&P 500 TR, o la estimación
      `=K<fila anterior>*<SP500 hoy>/<SP500 mes anterior>` con nota (sin dividendos).
    - I, L, M, N, O, P: **extender las fórmulas de la fila anterior** (I=`SUM(B:H)`, L=`(I−Iprev−J)/Iprev`,
      M=`(1+Mprev)*(1+L)−1`, N=`K/Kprev−1`, O=`(1+Oprev)*(1+N)−1`, P=`M−O`). Q: nota en texto.
  - **Movimientos** (fila 3 = encabezados): Fecha `dd/mm/aaaa` (texto), Tipo (Aporte/Retiro/Compra/Venta), Activo,
    Bloque, Monto USD (número), Cuenta, Afecta aporte neto (Sí/No), Nota. Se agrega al final.
  - **Watchlist** (fila 3 = encabezados, tickers desde la fila 4; debajo hay notas y el plan de NVDA):
    A Ticker, B Veredicto (`Categoría (puntaje/100)`), C Precio de entrada, D Valor justo conservador,
    E Precio de referencia, F Fecha del precio (fecha). **G–K son fórmulas** (semáforo, techo 5%, tramos).
    Para agregar un ticker: insertar una fila debajo del último ticker (no sobrescribir notas) y copiar las
    fórmulas G–K de la fila de arriba cambiando el número de fila.
  - **Plan**: reglas y checklist (solo lectura).
- Skill de análisis: `.claude/skills/lukai-equity-analyst/` (libro Excel Quality & Compounding; método del
  equity-analyst). Sus datos cuantitativos los llena `python -m lukai rubrica` desde EDGAR.
- Rúbrica: `rubrica/Rubrica_Quality_Compounding_2026.md`. Umbrales: `config/criterios.yaml`. Universo: `config/universo.yaml`.
- Plantilla de valoración en Sheets: `Rubrica_Quality_Compounding` (id `16sbQ_UAGSsJVy01ieZhEmusd09RFupM5ZrPnW6Xz8dM`).
- Ideas: `ideas.md`. Bitácora de decisiones: `diario/decisiones.md`. Análisis: `analisis/<TICKER>/`.
- Copias de los libros en Drive (opcional, paso 11 de `/analizar`): carpeta `LukAI/Análisis/<TICKER>`, un archivo
  por análisis convertido a Google Sheet. La plantilla `Rubrica_Quality_Compounding` de Drive nunca se modifica.

## Datos: fuentes y rutas alternas

`python -m lukai` usa primero fuentes oficiales y gratuitas, con caché local (`data/cache/`) y límites por fuente:

| Dato | Principal | Alterna 1 | Alterna 2 |
|---|---|---|---|
| Estados financieros | SEC EDGAR XBRL (10-K, 10-Q, 20-F) | Alpha Vantage | — |
| Precio | Alpha Vantage (clave en `ALPHAVANTAGE_API_KEY` o conector MCP) | Stooq | Yahoo (no oficial, marcado ⚠️) |
| Tasa libre de riesgo, S&P 500 | FRED | Alpha Vantage `TREASURY_YIELD` | — |

Uso eficiente del cupo de Alpha Vantage (25 llamadas/día gratis):
- El screener **no** usa Alpha Vantage para fundamentales; solo pide precio para el top 10.
- En `/analizar`, pedir por el conector solo: `GLOBAL_QUOTE` (precio), `TIME_SERIES_MONTHLY_ADJUSTED` (histórico)
  e `INCOME_STATEMENT` (verificación cruzada). Las respuestas grandes las guarda el conector en un archivo:
  pasar esa ruta a `--historico` / `--av-income` en lugar de copiar los datos.
- Para correr Python: `pip install -r requirements.txt` una vez; luego `python -m lukai --help`.

## Comandos de Python

```bash
python -m lukai screen [--top 10] [--sin-precios] [--solo T1,T2]
python -m lukai ficha TICKER --cartera <valor total USD> [--precio P --fecha-precio F] [--historico archivo] [--av-income archivo] [--fx X --adr N] [--fcf USD]
python -m lukai rubrica TICKER --precio P --historico csv --ingresos-ntm USD --eps-ntm X --peers C1,C2 [--precios-peers C1=p,C2=p]
python -m lukai completar analisis/T/<fecha>-rubrica.xlsx cualitativo.json   # escribe lo del agente y lee resultados
python -m lukai semaforo --precio P --entrada E --justo J --cartera <USD>
python -m lukai macro       # tasa 10 años y S&P 500 (FRED)
python -m lukai llamadas    # requests hechos hoy por fuente
python -m unittest discover -s tests
```

Emisores extranjeros (20-F, p. ej. SAP en EUR o TSM en TWD): la ficha avisa de la moneda; para valorar por ADR hay
que pasar `--fx` (USD por unidad de moneda local) y `--adr` (acciones ordinarias por ADR), con fuente citada.
