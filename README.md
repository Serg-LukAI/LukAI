# LukAI Inversor

Herramienta personal para invertir con proceso, sobre Claude Code:

```
/screener (trimestral) → Watchlist → /analizar TICKER (a demanda) → compra en tramos → /cierre-mes (mensual)
```

- **Datos verificables:** SEC EDGAR (10-K, 10-Q, 20-F) y FRED como fuentes principales. Alpha Vantage, Stooq y
  Yahoo son rutas alternas con fallback automático, caché local y control de cupo.
- **Cálculo determinista:** ratios, knockouts, puntaje, reverse DCF y semáforo los calcula `lukai/` (Python);
  los agentes interpretan, no hacen aritmética.
- **Subagentes:** `screener`, `equity-analyst`, `valuador`, `abogado-del-diablo`, `contador` (`.claude/agents/`).
- **Registro:** Sheet "Seguimiento inversiones" (siempre con confirmación) y `diario/decisiones.md` para aprender
  de las decisiones propias.

Instrucciones completas y reglas: [CLAUDE.md](CLAUDE.md).

```bash
pip install -r requirements.txt
python -m lukai screen --sin-precios     # ~3 min la primera vez; luego segundos (caché)
python -m lukai ficha NVDA --cartera 61747
python -m unittest discover -s tests
```

Opcional: `export ALPHAVANTAGE_API_KEY=...` para que Python pida precios directamente sin pasar por el conector.

*Uso personal. No constituye asesoría financiera.*

## Usarlo desde el celular (Claude Code en la nube)

1. En la app de Claude, abre **Code** → nueva sesión → repositorio **Serg-LukAI/LukAI** → entorno **LukAI**
   (tiene acceso a SEC EDGAR y FRED). Los conectores Google Sheets, Drive y Alpha Vantage ya están disponibles.
2. Usa los mismos comandos: `/screener`, `/analizar TICKER`, `/cierre-mes`.
3. Al terminar, el agente te pide OK para guardar en GitHub: dilo siempre, porque la sesión en la nube es temporal.
4. La primera corrida del screener en cada sesión tarda ~1–3 min (la caché no se conserva entre sesiones).

## ¿Qué se actualiza en Google Drive?

- **Sheet "Seguimiento inversiones — Sergio":** sí, con tu OK, desde los 3 comandos.
- **Libro de la rúbrica:** se guarda en `analisis/<TICKER>/` (GitHub). Copia opcional en Drive
  (`LukAI/Análisis/<TICKER>`) al final de `/analizar`; cuesta muchos tokens, por eso se pregunta.
