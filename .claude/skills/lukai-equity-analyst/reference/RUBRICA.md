# RUBRICA — Definición (Quality & Compounding)

Filosofía: **Calidad ≈ 70 / Valoración ≈ 30.** El margen de seguridad viene de la certeza sobre el negocio (moat, ROIC, pista de reinversión), no de pagar múltiplos bajos. La valoración es un guardarraíl evaluado en términos **relativos** (vs. historia propia, crecimiento y sector). Objetivo: encontrar grandes negocios que sigan siéndolo en 5–10 años, a un precio que no descuente la perfección.

## Parte 0 — Knockouts (descartan sin importar el resto)
- **K1** Decrecimiento estructural: CAGR de ingresos o EPS < 0%.
- **K2** Deterioro de márgenes: margen bruto cae > 3 pts en 5 años.
- **K3** ROIC < WACC (destruye valor).
- **K4** Deuda neta / EBITDA > 3.5x (revisar también vencimientos y tasa flotante). Usa **solo deuda financiera**; los arrendamientos operativos no cuentan aquí.
- **K5** Banderas contables (GAAP vs non-GAAP, caja dudosa, manipulación) — manual.

> **Definición de ROIC (K3 y C2):** `EBIT·(1−tasa) / capital invertido`, con
> **capital invertido = deuda financiera + patrimonio − caja + arrendamientos operativos**. Los leases NO se
> cuentan como deuda (K4/C6) pero SÍ entran en el capital invertido: financian activos operativos reales y, si se
> omiten, el ROIC se infla a niveles irreales en negocios lease-intensivos (CMG: ~96% sin leases vs. ~22% con leases).

## Parte 1 — Calidad (70 pts) · puntaje 0/1/2 por criterio
Cuantitativos (automáticos desde `Ratios`):
- **C2 ROIC** (15): 2 si ≥15% · 1 si 10–15% · 0 si <10%. Capital invertido **incluye arrendamientos operativos** (ver definición arriba).
- **C3 Crecimiento EPS CAGR 5a** (15): 2 si ≥12% · 1 si 8–12% · 0 si <8%.
- **C5 Δ margen EBITDA 5a** (5): 2 si expande ≥+1pt · 1 si estable · 0 si contrae.
- **C6 Deuda neta/EBITDA** (5): 2 si ≤2x/caja neta · 1 si 2–3.5x · 0 si >3.5x.

Cualitativos (vienen de la hoja `Cualitativo`, escala 1–5 mapeada a 0–2):
- **C1** (15) = promedio de Naturaleza + Moat + Poder de precios + Trayectoria del moat.
- **C4** (10) = promedio de Pista de reinversión + Vientos seculares + Opcionalidad.
- **C7** (5)  = promedio de Calidad directiva + Círculo de competencia.

## Parte 2 — Valoración como guardarraíl (30 pts)
- **V1 Fwd P/E vs. mediana propia 5a** (8): 2 si ≤1.0x · 1 si ≤1.3x · 0 si >1.3x.
- **V2 PEG forward** (8): 2 si ≤1.5 · 1 si ≤2.0 · 0 si >2.0 (laxo: se paga calidad).
- **V3 EV/EBITDA vs. mediana propia y sector** (7): 2 bajo ambas · 1 bajo una · 0 sobre ambas.
- **V4 FCF Yield NTM ajustado** (7): 2 si ≥4% · 1 si 2–4% (o bajo justificado por reinversión a alto ROIC) · 0 si <2%.

## Parte 3 — Clasificación
- **NO APTO (KNOCKOUT)** si cualquier K activo.
- **REVISAR — riesgo cualitativo alto** si Círculo de competencia = 1 o Riesgo de disrupción = 1.
- **COMPOUNDER DE CONVICCIÓN** si puntaje ≥ 75% y moat fuerte (C1 ≥ 1.5), sin lo anterior.
- **CALIDAD EN OBSERVACIÓN** si ≥ 55% sin knockouts (esperar mejor precio).
- **NO APTO** en otro caso.

## Valoración de precio (hoja `Valoración`)
- Valor justo = EPS NTM × mediana P/E histórica × factor (bajo 0.90 / alto 1.10, ajustables).
- Chequeo cruzado por FCF Yield objetivo (EV implícito → valor por acción).
- Conclusión BARATO / RAZONABLE / CARO y **rango ideal de compra** = valor justo × (1 − margen de seguridad).
- Para un Compounder de Convicción, una caída sin cambio de fundamentales = acumular, no vender.
