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
