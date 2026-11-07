---
description: Análisis profundo de una acción — rúbrica, valoración, abogado del diablo y precio de entrada
argument-hint: "TICKER"
---

Analiza a fondo **$ARGUMENTS** con la rúbrica Calidad & Compounding.

## 1. Datos verificados (tú, antes de delegar)

1. Valor total de la cartera: `Resumen!E3` del Sheet (conector Google Sheets).
2. Por el conector Alpha Vantage (3 llamadas; el cupo gratuito es de 25 al día):
   - `GLOBAL_QUOTE` → precio y fecha.
   - `TIME_SERIES_MONTHLY_ADJUSTED` → si la respuesta queda guardada en un archivo, usa esa ruta. Si llega en el
     chat, guarda solo las últimas 61 filas `fecha,adjusted close` en
     `analisis/$ARGUMENTS/historico.csv`.
   - `INCOME_STATEMENT` → ruta del archivo guardado (para la verificación cruzada).
   Si ya existe una ficha de hoy en `analisis/$ARGUMENTS/`, no repitas llamadas.
3. Corre:
   `python -m lukai ficha $ARGUMENTS --cartera <E3> --precio <p> --fecha-precio <f> --historico <archivo> --av-income <archivo>`
   Si es un emisor extranjero (la ficha avisa de la moneda), consigue el tipo de cambio (`CURRENCY_EXCHANGE_RATE`)
   y el ratio del ADR (citado del 20-F) y vuelve a correrla con `--fx` y `--adr`.

## 2. Análisis (subagentes)

4. **equity-analyst** → knockouts cualitativos, 7 criterios de calidad, 2 comparables y puntaje /70.
5. **valuador** → criterios 8–12, reverse DCF, valor justo conservador, precio de entrada, semáforo, tramos,
   puntaje /30 y veredicto preliminar.
6. **abogado-del-diablo** → con contexto limpio: pásale solo el borrador y la ruta de la ficha. Puede bajar el
   veredicto, nunca subirlo.

## 3. Resultado para Sergio (una página)

- **Veredicto** (categoría y puntaje /100) · **precio de entrada** · **valor justo conservador** · **semáforo** hoy.
- **Checklist del satélite** (pestaña Plan, sección 6), punto por punto: ✅/❌. El punto 1 queda ⏳ hasta que
  Sergio escriba sus 3 líneas.
- Los 3 riesgos a vigilar con fecha, y el plan de tramos (montos y fechas según el calendario del último lunes
  del mes y la regla de 14 días).
- La pregunta del abogado del diablo.

## 4. Cierre (solo con OK de Sergio)

7. Pide a Sergio **sus 3 líneas** de cómo gana dinero la empresa. Sin ellas no hay paso a compra.
8. Propón la actualización de la fila del ticker en Watchlist (A–F; G–K son fórmulas). Si el ticker no está,
   inserta una fila debajo del último ticker. Escribe solo tras el OK.
9. Guarda el informe en `analisis/$ARGUMENTS/<fecha>.md`: resultado + secciones de calidad, valoración y revisión
   + las 3 líneas de Sergio.
10. Agrega la decisión a `diario/decisiones.md` con la plantilla del archivo, incluyendo el precio del día y la
    fecha de revisión (próximo reporte trimestral).
