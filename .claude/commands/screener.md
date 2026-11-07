---
description: Screener trimestral — propone candidatos para la Watchlist con datos de SEC EDGAR
argument-hint: "[--solo T1,T2] [--sin-precios]"
---

Corre el screener trimestral de LukAI. Argumentos opcionales: $ARGUMENTS

1. Delega en el subagente **screener**: que ejecute `python -m lukai screen $ARGUMENTS` y devuelva las fichas de
   una línea del top 10, las ideas de `ideas.md` y el conteo.
2. Lee la pestaña Watchlist del Sheet (`Watchlist!A1:F12`) para saber qué tickers ya están y cuántos hay
   (el máximo es 8, según CLAUDE.md).
3. Muestra a Sergio el top 10 y pregúntale cuáles quiere **estudiar** (1–3). Recuérdale: entrar a la Watchlist
   no es comprar; el veredicto y el precio de entrada salen de `/analizar`.
4. Con su elección, propón la inserción en la Watchlist. Por cada ticker: insertar una fila debajo del último
   ticker con A = ticker, B = `Pendiente análisis`, C–F vacías, y G–K copiando las fórmulas de la fila de arriba.
   Si se pasa de 8 nombres, pregunta cuál sale. **Escribe solo tras su OK.**
5. Agrega a `diario/decisiones.md` una entrada por ticker elegido (y por los descartados que Sergio quiera
   recordar), con la plantilla del archivo: tipo `Entra a watchlist`, motivo en palabras de Sergio y cifras clave.
6. Termina con el siguiente paso sugerido: `/analizar <ticker>` para 1–2 de ellos este trimestre.
