---
description: Análisis profundo de una acción — skill lukai-equity-analyst, valoración, abogado del diablo y precio de entrada
argument-hint: "TICKER"
---

Analiza a fondo **$ARGUMENTS** con la rúbrica Quality & Compounding (skill `lukai-equity-analyst`).

## 1. Datos verificados (tú, antes de delegar)

1. Valor total de la cartera: `Resumen!E3` del Sheet (conector Google Sheets).
2. Por el conector Alpha Vantage, una llamada por endpoint (el cupo gratuito es de 25 al día). Si ya hay archivos
   de hoy en `analisis/$ARGUMENTS/`, no repitas llamadas.
   - `GLOBAL_QUOTE` → precio y fecha.
   - `TIME_SERIES_MONTHLY_ADJUSTED` → guarda solo las últimas 61 filas `fecha,adjusted close` en
     `analisis/$ARGUMENTS/historico.csv` (o pasa la ruta del archivo si el conector lo guardó).
   - `INCOME_STATEMENT` → ruta del archivo guardado (verificación cruzada).
   - `EARNINGS_ESTIMATES` → ingresos y EPS del año fiscal que cubra la mayor parte de los próximos 12 meses
     (conservador: si dudas, el más cercano). Anota cuál usaste.
   - Lo mismo `GLOBAL_QUOTE` para los 2 competidores.
3. Ficha (verificación cruzada, reverse DCF):
   `python -m lukai ficha $ARGUMENTS --cartera <E3> --precio <p> --fecha-precio <f> --historico <csv> --av-income <archivo>`
4. Libro de la skill:
   `python -m lukai rubrica $ARGUMENTS --precio <p> --historico <csv> --ingresos-ntm <USD> --eps-ntm <x> --etiqueta-ntm "<FY>E Alpha Vantage" --peers <C1>,<C2> --precios-peers <C1>=<p>,<C2>=<p>`
   Emisores extranjeros (la ficha avisa de la moneda): `CURRENCY_EXCHANGE_RATE` y el ratio del ADR citado del
   20-F, y la ficha con `--fx` y `--adr`. El libro de la skill es para emisores de EE. UU.: para extranjeros,
   el análisis se apoya en la ficha.

## 2. Análisis (subagentes)

5. **equity-analyst** → cualitativo, K5, brechas, `python -m lukai completar` → clasificación y calidad /70.
6. **valuador** → valor justo conservador, contraste con el reverse DCF, precio de entrada, semáforo, tramos y
   valoración /30.
7. **abogado-del-diablo** → con contexto limpio: solo el borrador, la ficha y el .xlsx. Puede bajar el veredicto,
   nunca subirlo.

## 3. Resultado para Sergio (una página)

- **Veredicto** (clasificación del libro y puntaje /100, confianza por momentum) · **precio de entrada** ·
  **valor justo conservador** · **semáforo** hoy · prima o descuento.
- **Checklist del satélite** (pestaña Plan, sección 6), punto por punto: ✅/❌. El punto 1 queda ⏳ hasta que
  Sergio escriba sus 3 líneas.
- Los 3 riesgos a vigilar con fecha, el plan de tramos (montos y fechas según el último lunes del mes y la regla
  de ≥ 14 días) y las brechas de datos.
- La pregunta del abogado del diablo.
- Ruta del libro: `analisis/$ARGUMENTS/<fecha>-rubrica.xlsx` (Excel lo recalcula al abrir).

## 4. Cierre (solo con OK de Sergio)

8. Pide a Sergio **sus 3 líneas** de cómo gana dinero la empresa. Sin ellas no hay paso a compra. Escríbelas
   también en `Cualitativo!B29` con `python -m lukai completar`.
9. Propón la actualización de la fila del ticker en Watchlist (A–F; G–K son fórmulas). Si no está, inserta una
   fila debajo del último ticker. Escribe solo tras el OK.
10. Guarda el informe en `analisis/$ARGUMENTS/<fecha>.md` y agrega la decisión a `diario/decisiones.md` con su
    plantilla (precio del día y fecha de revisión = próximo reporte).
