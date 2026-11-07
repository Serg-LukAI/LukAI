from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.chart import LineChart, BarChart, Reference
import argparse, sys, re

_p = argparse.ArgumentParser(description="Genera la plantilla de rúbrica Quality & Compounding.")
_p.add_argument("--company", default="EMPRESA X", help="Nombre o ticker de la empresa analizada")
_p.add_argument("--out", default="/home/claude/work/Rubrica_Quality_Compounding.xlsx", help="Ruta de salida .xlsx")
_p.add_argument("--blank", action="store_true", help="Genera la plantilla con las celdas de entrada vacías (sin datos de ejemplo)")
_p.add_argument("--years", default=None,
                help="6 etiquetas de período separadas por coma (4 FY históricos + TTM + NTM), p. ej. "
                     "'FY2022,FY2023,FY2024,FY2025,TTM 2026,NTM 2026E'. Si se omite, se usan placeholders "
                     "relativos que el flujo DEBE sobreescribir (Datos!B4:G4) con los años reales cargados.")
ARGS = _p.parse_args()
COMPANY = ARGS.company
# Etiqueta corta para celdas estrechas y títulos de gráficos: el ticker entre paréntesis si existe,
# si no, el nombre completo. Ej.: "Chipotle Mexican Grill (CMG)" -> "CMG".
_m = re.search(r"\(([^)]+)\)", COMPANY)
COMPANY_SHORT = _m.group(1).strip() if _m else COMPANY

ARIAL = "Arial"
BLUE = Font(name=ARIAL, color="0000FF", size=10)
BLACK = Font(name=ARIAL, color="000000", size=10)
GREEN = Font(name=ARIAL, color="008000", size=10)
BOLD = Font(name=ARIAL, bold=True, size=10)
BOLDG = Font(name=ARIAL, bold=True, color="008000", size=10)
BOLDB = Font(name=ARIAL, bold=True, color="0000FF", size=10)
H1 = Font(name=ARIAL, bold=True, size=14, color="1F3864")
H2 = Font(name=ARIAL, bold=True, size=10, color="FFFFFF")
NOTE = Font(name=ARIAL, italic=True, size=9, color="7F7F7F")
HDRFILL = PatternFill("solid", start_color="1F3864")
SECFILL = PatternFill("solid", start_color="4472C4")
YEL = PatternFill("solid", start_color="FFF2CC")
GREYF = PatternFill("solid", start_color="F2F2F2")
GREENF = PatternFill("solid", start_color="C6EFCE")
AMBF = PatternFill("solid", start_color="FFEB9C")
REDF = PatternFill("solid", start_color="FFC7CE")
thin = Side(style="thin", color="BFBFBF")
BORD = Border(left=thin, right=thin, top=thin, bottom=thin)
PCT = "0.0%"
MULT = '0.0"x"'
MONEY = '$#,##0;($#,##0);"-"'
PRICE = '$#,##0.00'

def put(ws, cell, value, font=BLACK, fill=None, fmt=None, align=None, wrap=False):
    # Guardia: una NOTA/descripción (font NOTE) que empiece por "=" la interpretaría Excel como
    # fórmula y daría #VALUE!/#NAME?. Las fórmulas reales usan otras fuentes (BLACK/GREEN/BOLD...).
    if font is NOTE and isinstance(value, str) and value.startswith("="):
        value = "Fórmula: " + value[1:].lstrip()
    c = ws[cell]
    c.value = value
    c.font = font
    if fill: c.fill = fill
    if fmt: c.number_format = fmt
    c.border = BORD
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    return c

wb = Workbook()

# ================= Instrucciones =================
ins = wb.active
ins.title = "Instrucciones"
ins.sheet_view.showGridLines = False
ins.column_dimensions["A"].width = 3
ins.column_dimensions["B"].width = 115
ins["B2"] = "Rúbrica Quality & Compounding — Plantilla de Análisis Comparativo"
ins["B2"].font = H1
texts = [
 ("CÓMO USAR ESTE ARCHIVO", BOLD),
 (f"1. Hoja 'Datos': diligencia los rubros base de {COMPANY} — 4 años fiscales + TTM (5 períodos históricos) + 1 proyección NTM. Todo lo AZUL sobre fondo amarillo es entrada manual. Reescribe los encabezados de período (B4:G4) con los años fiscales reales.", BLACK),
 ("2. Hoja 'Ratios': 100% automática (márgenes, ROIC, múltiplos, CAGR, medianas históricas). No editar.", BLACK),
 ("3. Hoja 'Cualitativo': el corazón del análisis de criterio. Escala 1/3/5 con descripciones ancladas. Bloque A = el negocio HOY (naturaleza, moat, poder de precios, dirección, círculo de competencia). Bloque B = la MIRADA AL FUTURO (trayectoria del moat, pista de reinversión, vientos seculares, riesgo de disrupción, opcionalidad). Estos puntajes alimentan solos los criterios cualitativos de la Rúbrica.", BLACK),
 (f"4. Hoja 'Comparables': diligencia las métricas de los 2 competidores principales y el promedio del sector. La columna {COMPANY_SHORT} se llena sola. El selector de métrica (celda B19) alimenta el gráfico comparador dinámico.", BLACK),
 ("5. Hoja 'Rúbrica': revisa los knockouts automáticos y responde la bandera contable (manual). Los criterios cuantitativos se puntúan solos y los cualitativos se traen de la hoja 'Cualitativo'. Puntaje total y clasificación se calculan solos.", BLACK),
 ("6. Hoja 'Valoración': ajusta precio actual ('Datos' B23), margen de seguridad y factores de P/E objetivo. Obtienes la conclusión BARATO / RAZONABLE / CARO y el rango ideal de compra.", BLACK),
 ("7. Hoja 'Gráficos': se actualizan automáticamente al cambiar los datos (abrir el archivo en Excel recalcula todo).", BLACK),
 ("", BLACK),
 ("CÓDIGO DE COLORES (estándar financiero)", BOLD),
 ("• Texto AZUL sobre fondo amarillo = entrada manual que debes diligenciar/reemplazar.", BLACK),
 ("• Texto NEGRO = fórmula/cálculo. No editar.   • Texto VERDE = vínculo desde otra hoja. No editar.", BLACK),
 ("", BLACK),
 ("FILOSOFÍA DE LA RÚBRICA", BOLD),
 ("Calidad ≈ 70% del puntaje · Valoración ≈ 30%. El margen de seguridad viene de la certeza sobre el negocio (moat, ROIC, pista de reinversión), no de múltiplos bajos absolutos. La valoración se evalúa en términos RELATIVOS: vs. historia propia, vs. crecimiento (PEG) y vs. sector.", BLACK),
 ("Usa FCF AJUSTADO (no GAAP) cuando el negocio tenga float u otras distorsiones (caso MELI / Mercado Pago).", BLACK),
 ("", BLACK),
 ("Herramienta de análisis personal. No constituye asesoría financiera ni recomendación de valores específicos.", NOTE),
]
r = 4
for t, f in texts:
    ins[f"B{r}"] = t
    ins[f"B{r}"].font = f
    ins[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    r += 1

# ================= Datos =================
d = wb.create_sheet("Datos")
d.sheet_view.showGridLines = False
d.column_dimensions["A"].width = 38
for col in "BCDEFG": d.column_dimensions[col].width = 13
d.column_dimensions["H"].width = 48
d["A1"] = f"DATOS BASE — {COMPANY}"
d["A1"].font = H1
d["A2"] = "Valores precargados = EJEMPLO (aprox. Alphabet Inc., GOOGL). Reemplazar con datos reales (10-K, FMP, SEC EDGAR)." if not ARGS.blank else "Plantilla vacía. Diligenciar celdas azules con datos oficiales."
d["A2"].font = NOTE
put(d, "A4", "Métrica (unidades)", H2, HDRFILL, align="left")
# Etiquetas de período DINÁMICAS. Por defecto son placeholders relativos (nunca quedan
# desfasadas como un año fijo); el flujo sobreescribe Datos!B4:G4 con los años fiscales reales.
if ARGS.years:
    years = [y.strip() for y in ARGS.years.split(",")]
    if len(years) != 6:
        sys.exit("ERROR: --years requiere exactamente 6 etiquetas separadas por coma (4 FY + TTM + NTM).")
else:
    years = ["FY-4", "FY-3", "FY-2", "FY-1", "TTM", "NTM"]
for i, y in enumerate(years):
    put(d, f"{get_column_letter(2+i)}4", y, BOLDB, YEL, None, "center")
put(d, "H4", "Fuente / Notas", H2, HDRFILL, align="left")

metrics = [
 ("Ingresos ($mm)", [257637, 282836, 307394, 350018, 402000, 462000], MONEY),
 ("Utilidad bruta ($mm)", [146698, 156633, 174062, 203712, 238000, 275000], MONEY),
 ("EBITDA ($mm)", [106400, 109200, 118700, 150500, 177700, 215800], MONEY),
 ("EBIT ($mm)", [78714, 74842, 84293, 112390, 135000, 165000], MONEY),
 ("Utilidad neta ($mm)", [76033, 59972, 73795, 100118, 125000, 150000], MONEY),
 ("EPS diluido ($)", [5.61, 4.56, 5.80, 8.04, 10.20, 12.40], PRICE),
 ("Acciones diluidas (mm)", [13553, 13159, 12722, 12447, 12250, 12100], '#,##0'),
 ("Flujo de caja operativo ($mm)", [91652, 91495, 101746, 125299, 150000, 175000], MONEY),
 ("Capex ($mm)", [24640, 31485, 32251, 52535, 85000, 95000], MONEY),
 ("FCF ajustado ($mm)", [67012, 60010, 69495, 72764, 65000, 80000], MONEY),
 ("Caja e inversiones ($mm)", [139649, 113762, 110916, 95657, 100000, 110000], MONEY),
 ("Deuda total ($mm)", [28810, 29679, 29857, 28930, 30000, 30000], MONEY),
 ("Patrimonio ($mm)", [251635, 256144, 283379, 325084, 360000, 400000], MONEY),
 ("Activos totales ($mm)", [359268, 365264, 402392, 450256, 500000, 550000], MONEY),
 ("Tasa impositiva efectiva (%)", [0.162, 0.159, 0.139, 0.164, 0.165, 0.165], PCT),
 ("Precio acción del período ($)", [144.85, 88.23, 139.69, 189.30, None, None], PRICE),
]
# Notas por defecto específicas por métrica (recordatorios de reglas que distorsionan el análisis).
ROW_NOTES = {
 "Deuda total ($mm)": ("SOLO deuda financiera (préstamos, bonos, leasing financiero). EXCLUYE pasivos por "
                       "ARRENDAMIENTO OPERATIVO (ASC 842) y anótalos aquí: 'leases op. ≈ $X mm'. Meterlos como "
                       "deuda distorsiona DN/EBITDA, EV/EBITDA y el relato de 'caja neta' (restaurantes/retail)."),
 "FCF ajustado ($mm)": ("OCF − |Capex|. Ajusta por float / fintech / partidas no recurrentes (lección MELI): "
                        "usa el FCF ajustado que reporta la empresa cuando aplique."),
 "Caja e inversiones ($mm)": "Incluye caja + inversiones de corto plazo (no inversiones estratégicas de largo plazo).",
}
r = 5
for name, vals, fmt in metrics:
    put(d, f"A{r}", name, BOLD, GREYF, align="left")
    for i, v in enumerate(vals):
        vv = None if ARGS.blank else v
        if vv is not None:
            put(d, f"{get_column_letter(2+i)}{r}", vv, BLUE, YEL, fmt, "right")
        else:
            put(d, f"{get_column_letter(2+i)}{r}", None, BLUE, YEL, fmt, "right")
    note = ROW_NOTES.get(name, "Fuente: [10-K / FMP / EDGAR], [fecha], [referencia]")
    put(d, f"H{r}", note, NOTE, align="left", wrap=True)
    r += 1
put(d, "F20", "='Datos'!$B$23", GREEN, None, PRICE, "right")
put(d, "G20", "='Datos'!$B$23", GREEN, None, PRICE, "right")
d["H20"] = "TTM y NTM usan el precio actual (B23)"
d["H20"].font = NOTE
# Fila 21: arrendamientos operativos. NO son deuda financiera (no van en la fila 16, no tocan
# DN/EBITDA ni EV/EBITDA), pero SÍ entran en el capital invertido del ROIC (lección CMG).
put(d, "A21", "Arrendamientos operativos ($mm)", BOLD, GREYF, align="left")
_lease_ex = [12734, 13660, 14091, 14951, 14951, 15000]
for i in range(6):
    cl = get_column_letter(2+i)
    put(d, f"{cl}21", (None if ARGS.blank else _lease_ex[i]), BLUE, YEL, MONEY, "right")
put(d, "H21", "Pasivo por arrendamiento operativo / activo ROU (ASC 842). NO es deuda financiera "
              "(no va en fila 16, no afecta DN/EBITDA ni EV/EBITDA), pero SÍ se suma al capital invertido "
              "del ROIC. Pon 0 si el negocio casi no usa leases.", NOTE, align="left", wrap=True)
put(d, "A22", "WACC estimado (%)", BOLD, GREYF, align="left")
put(d, "B22", (None if ARGS.blank else 0.09), BLUE, YEL, PCT, "right")
put(d, "H22", "Costo de capital estimado de la empresa", NOTE, align="left")
put(d, "A23", "PRECIO ACTUAL DE MERCADO ($)", BOLD, GREYF, align="left")
put(d, "B23", (None if ARGS.blank else 250.00), BLUE, YEL, PRICE, "right")
put(d, "H23", "Actualizar cada vez que se use el modelo", NOTE, align="left")

# ================= Ratios =================
rt = wb.create_sheet("Ratios")
rt.sheet_view.showGridLines = False
rt.column_dimensions["A"].width = 32
for col in "BCDEFG": rt.column_dimensions[col].width = 11.5
rt.column_dimensions["H"].width = 28
rt.column_dimensions["I"].width = 11
rt["A1"] = f"RATIOS CALCULADOS — {COMPANY}"
rt["A1"].font = H1
rt["A2"] = "Hoja 100% automática. No editar."
rt["A2"].font = NOTE
put(rt, "A4", "Ratio", H2, HDRFILL, align="left")
for i in range(6):
    cl = get_column_letter(2+i)
    put(rt, f"{cl}4", f"=Datos!{cl}4", BOLDG, GREYF, None, "center")

def F(formula):
    return "=IFERROR(" + formula + ',"")'

ratio_defs = [
 ("Margen bruto", lambda c, p: F(f"Datos!{c}6/Datos!{c}5"), PCT, False),
 ("Margen EBITDA", lambda c, p: F(f"Datos!{c}7/Datos!{c}5"), PCT, False),
 ("Margen neto", lambda c, p: F(f"Datos!{c}9/Datos!{c}5"), PCT, False),
 ("Crecimiento ingresos YoY", lambda c, p: F(f"(Datos!{c}5/Datos!{p}5)-1"), PCT, True),
 ("Crecimiento EPS YoY", lambda c, p: F(f"(Datos!{c}10/Datos!{p}10)-1"), PCT, True),
 ("ROE", lambda c, p: F(f"Datos!{c}9/Datos!{c}17"), PCT, False),
 ("ROA", lambda c, p: F(f"Datos!{c}9/Datos!{c}18"), PCT, False),
 # Capital invertido = deuda financiera + patrimonio − caja + arrendamientos operativos (fila 21).
 # Los leases NO son deuda financiera pero financian activos operativos reales: incluirlos evita
 # que el ROIC se dispare a niveles irreales en negocios lease-intensivos (restaurantes/retail).
 ("ROIC", lambda c, p: F(f"(Datos!{c}8*(1-Datos!{c}19))/(Datos!{c}16+Datos!{c}17-Datos!{c}15+Datos!{c}21)"), PCT, False),
 ("Deuda neta ($mm)", lambda c, p: F(f"Datos!{c}16-Datos!{c}15"), MONEY, False),
 ("Deuda neta / EBITDA", lambda c, p: F(f"(Datos!{c}16-Datos!{c}15)/Datos!{c}7"), MULT, False),
 ("Market cap ($mm)", lambda c, p: F(f"Datos!{c}20*Datos!{c}11"), MONEY, False),
 ("Enterprise Value ($mm)", lambda c, p: F(f"{c}15+{c}13"), MONEY, False),
 ("P/E", lambda c, p: F(f"Datos!{c}20/Datos!{c}10"), MULT, False),
 ("EV / EBITDA", lambda c, p: F(f"{c}16/Datos!{c}7"), MULT, False),
 ("P/S", lambda c, p: F(f"{c}15/Datos!{c}5"), MULT, False),
 ("FCF Yield (ajustado, s/EV)", lambda c, p: F(f"Datos!{c}14/{c}16"), PCT, False),
]
r = 5
for name, fn, fmt, skip_first in ratio_defs:
    put(rt, f"A{r}", name, BOLD, GREYF, align="left")
    for i in range(6):
        cl = get_column_letter(2+i)
        pl = get_column_letter(1+i)
        if skip_first and i == 0:
            put(rt, f"{cl}{r}", None, BLACK, None, fmt, "right")
        else:
            put(rt, f"{cl}{r}", fn(cl, pl), BLACK, None, fmt, "right")
    r += 1

put(rt, "H4", "Resumen 5a / forward", H2, SECFILL, align="left")
put(rt, "I4", "Valor", H2, SECFILL, align="center")
summary = [
 ("CAGR ingresos 5a", F("(Datos!F5/Datos!B5)^(1/4)-1"), PCT),          # I5
 ("CAGR EPS 5a", F("(Datos!F10/Datos!B10)^(1/4)-1"), PCT),             # I6
 ("Mediana P/E 5a (hist.)", F("MEDIAN(B17:F17)"), MULT),               # I7
 ("Mediana EV/EBITDA 5a (hist.)", F("MEDIAN(B18:F18)"), MULT),         # I8
 ("P/E forward (NTM)", F("G17"), MULT),                                # I9
 ("PEG forward", F("G17/(G9*100)"), '0.00'),                           # I10
 ("FCF Yield NTM (ajustado)", F("G20"), PCT),                          # I11
 ("Crec. EPS NTM", F("G9"), PCT),                                      # I12
]
r = 5
for name, f, fmt in summary:
    put(rt, f"H{r}", name, BOLD, GREYF, align="left")
    put(rt, f"I{r}", f, BLACK, None, fmt, "right")
    r += 1

# ================= Comparables =================
cp = wb.create_sheet("Comparables")
cp.sheet_view.showGridLines = False
cp.column_dimensions["A"].width = 30
for col in "BCDE": cp.column_dimensions[col].width = 16
cp.column_dimensions["F"].width = 42
cp["A1"] = f"COMPARABLES — {COMPANY} vs. COMPETIDORES vs. SECTOR"
cp["A1"].font = H1
cp["A2"] = "Columnas C, D y E = entrada manual (TTM / forward). Ejemplos precargados: reemplazar. Renombra los encabezados con los nombres reales."
cp["A2"].font = NOTE
put(cp, "A4", "Métrica", H2, HDRFILL, align="left")
put(cp, "B4", COMPANY_SHORT, H2, HDRFILL, align="center")
put(cp, "C4", "Competidor 1", BOLDB, YEL, None, "center")
put(cp, "D4", "Competidor 2", BOLDB, YEL, None, "center")
put(cp, "E4", "Promedio sector", BOLDB, YEL, None, "center")
put(cp, "F4", "Notas", H2, HDRFILL, align="left")

comp_rows = [
 ("Crec. ingresos NTM", "=IFERROR(Ratios!G8,\"\")", PCT, [0.14, 0.16, 0.12]),
 ("CAGR EPS 5a", "=IFERROR(Ratios!I6,\"\")", PCT, [0.15, 0.20, 0.12]),
 ("Margen bruto (TTM)", "=IFERROR(Ratios!F5,\"\")", PCT, [0.69, 0.81, 0.60]),
 ("Margen EBITDA (TTM)", "=IFERROR(Ratios!F6,\"\")", PCT, [0.53, 0.55, 0.45]),
 ("ROE (TTM)", "=IFERROR(Ratios!F10,\"\")", PCT, [0.35, 0.32, 0.25]),
 ("ROIC (TTM)", "=IFERROR(Ratios!F12,\"\")", PCT, [0.28, 0.26, 0.20]),
 ("Deuda neta / EBITDA", "=IFERROR(Ratios!F14,\"\")", MULT, [0.2, -0.3, 0.5]),
 ("P/E (TTM)", "=IFERROR(Ratios!F17,\"\")", MULT, [33.0, 24.0, 28.0]),
 ("P/E forward", "=IFERROR(Ratios!G17,\"\")", MULT, [29.0, 21.0, 25.0]),
 ("EV / EBITDA (TTM)", "=IFERROR(Ratios!F18,\"\")", MULT, [22.0, 15.0, 18.0]),
 ("FCF Yield (ajustado)", "=IFERROR(Ratios!F20,\"\")", PCT, [0.025, 0.035, 0.030]),
]
r = 5
for name, f, fmt, vals in comp_rows:
    put(cp, f"A{r}", name, BOLD, GREYF, align="left")
    put(cp, f"B{r}", f, GREEN, None, fmt, "right")
    for j, v in enumerate(vals):
        put(cp, f"{get_column_letter(3+j)}{r}", (None if ARGS.blank else v), BLUE, YEL, fmt, "right")
    put(cp, f"F{r}", "", NOTE, align="left")
    r += 1
# rows 5..15

put(cp, "A18", "COMPARADOR DINÁMICO", H2, SECFILL, align="left")
put(cp, "B18", "", H2, SECFILL); put(cp, "C18", "", H2, SECFILL)
put(cp, "D18", "", H2, SECFILL); put(cp, "E18", "", H2, SECFILL)
put(cp, "A19", "Selecciona la métrica a comparar →", BOLD, GREYF, align="left")
put(cp, "B19", "ROIC (TTM)", BLUE, YEL, None, "center")
dv = DataValidation(type="list", formula1="=$A$5:$A$15", allow_blank=False, showDropDown=False)
cp.add_data_validation(dv)
dv.add(cp["B19"])
put(cp, "A21", "Métrica seleccionada", BOLD, GREYF, align="left")
put(cp, "B21", COMPANY_SHORT, BOLD, GREYF, align="center")
put(cp, "C21", "Competidor 1", BOLD, GREYF, align="center")
put(cp, "D21", "Competidor 2", BOLD, GREYF, align="center")
put(cp, "E21", "Promedio sector", BOLD, GREYF, align="center")
put(cp, "A22", "=$B$19", BLACK, None, None, "left")
for j, col in enumerate("BCDE"):
    put(cp, f"{col}22", f"=IFERROR(INDEX({col}$5:{col}$15,MATCH($B$19,$A$5:$A$15,0)),\"\")", BLACK, None, '0.00', "right")

# ================= Cualitativo =================
cu = wb.create_sheet("Cualitativo", index=4)
cu.sheet_view.showGridLines = False
cu.column_dimensions["A"].width = 24
cu.column_dimensions["B"].width = 30
cu.column_dimensions["C"].width = 34
cu.column_dimensions["D"].width = 34
cu.column_dimensions["E"].width = 34
cu.column_dimensions["F"].width = 13
cu.column_dimensions["G"].width = 40
cu["A1"] = "ANÁLISIS CUALITATIVO — ¿GRAN NEGOCIO HOY Y SEGUIRÁ SIÉNDOLO?"
cu["A1"].font = H1
cu["A2"] = ("Escala 1 = Alerta (Evitar) · 3 = Neutro · 5 = Excelente (Ideal). Diligencia solo la columna 'Puntaje' (azul). "
           "El Bloque A juzga el negocio HOY; el Bloque B —lo más importante— proyecta si la ventaja sobrevive 5–10 años. "
           "Estos puntajes alimentan automáticamente los criterios cualitativos de la hoja 'Rúbrica'.")
cu["A2"].font = NOTE
cu.merge_cells("A2:G2")
cu.row_dimensions[2].height = 42

dv_135 = DataValidation(type="list", formula1='"1,3,5"', allow_blank=False)
cu.add_data_validation(dv_135)

def qual_header(row):
    put(cu, f"A{row}", "Criterio", BOLD, GREYF, align="left")
    put(cu, f"B{row}", "Pregunta clave de análisis", BOLD, GREYF, align="left")
    put(cu, f"C{row}", "1 – Alerta (Evitar)", BOLD, REDF, align="left")
    put(cu, f"D{row}", "3 – Neutro", BOLD, AMBF, align="left")
    put(cu, f"E{row}", "5 – Excelente (Ideal)", BOLD, GREENF, align="left")
    put(cu, f"F{row}", "Puntaje (1/3/5)", BOLD, GREYF, align="center")
    put(cu, f"G{row}", "Tus notas / evidencia", BOLD, GREYF, align="left")

def qual_row(row, crit, q, a1, a3, a5, default):
    put(cu, f"A{row}", crit, BOLD, None, align="left", wrap=True)
    put(cu, f"B{row}", q, BLACK, None, align="left", wrap=True)
    put(cu, f"C{row}", a1, BLACK, None, align="left", wrap=True)
    put(cu, f"D{row}", a3, BLACK, None, align="left", wrap=True)
    put(cu, f"E{row}", a5, BLACK, None, align="left", wrap=True)
    put(cu, f"F{row}", (None if ARGS.blank else default), BLUE, YEL, '0', "center")
    dv_135.add(cu[f"F{row}"])
    put(cu, f"G{row}", "", BLACK, None, align="left", wrap=True)
    cu.row_dimensions[row].height = 78

# BLOQUE A — EL NEGOCIO HOY
put(cu, "A4", "BLOQUE A — EL NEGOCIO HOY  (¿es un gran negocio ahora?)", H2, HDRFILL, align="left")
for col in "BCDEFG": put(cu, f"{col}4", "", H2, HDRFILL)
qual_header(5)
blockA = [
 ("1. Naturaleza del Negocio", '¿Es un "monopolio del consumidor" o una "commodity"?',
  "Commodity: vende por precio, sin lealtad de marca y con márgenes estrechos.",
  "Marca reconocida pero con competencia fuerte que limita el crecimiento.",
  "Monopolio del consumidor: producto que el cliente pide por su nombre.", 5),
 ("2. Foso Competitivo (Moat)", '¿Tiene barreras de entrada o es un "puente de peaje"?',
  "Nulo: fácil de copiar, sin patentes, red ni ventaja de escala.",
  "Ventaja temporal (p. ej. una moda) con riesgo de ser superada pronto.",
  'Sólido: única opción razonable en su nicho; costes de cambio altísimos.', 5),
 ("3. Poder de Precios", "¿Puede subir precios con la inflación sin perder clientes?",
  "Nulo: si sube precios, el cliente se va a la competencia de inmediato.",
  "Puede subir precios pero el volumen de ventas se resiente.",
  "Alto: sube precios por encima de la inflación sin sacrificar volumen.", 5),
 ("4. Calidad Directiva", '¿Tienen "skin in the game" y asignan bien el capital?',
  'Sin incentivos: directivos sin acciones, sueldos excesivos, "delirios de grandeza".',
  "Directivos profesionales pero sin visión clara de largo plazo.",
  "Dueños-gestores alineados; priorizan al accionista sobre su propio imperio.", 5),
 ("5. Círculo de Competencia", "¿Entiendo cómo gana dinero y cuáles son sus riesgos?",
  "Negocio demasiado complejo o fuera de mi área de conocimiento.",
  "Entiendo el producto pero no el entorno macro o competitivo.",
  "Conozco el sector, sé por qué gana a la competencia y detecto sus riesgos.", 5),
]
r = 6
for c, q, a1, a3, a5, df in blockA:
    qual_row(r, c, q, a1, a3, a5, df)
    r += 1

# BLOQUE B — LA MIRADA AL FUTURO
put(cu, "A12", "BLOQUE B — LA MIRADA AL FUTURO  (¿seguirá siéndolo en 5–10 años? — lo decisivo)", H2, HDRFILL, align="left")
for col in "BCDEFG": put(cu, f"{col}12", "", H2, HDRFILL)
qual_header(13)
blockB = [
 ("6. Trayectoria del Moat", "En 5–10 años, ¿el foso se ensancha o se erosiona?",
  "Se erosiona: disrupción, pérdida de relevancia, competencia ganando terreno.",
  "Estable: se mantiene, pero sin señales de fortalecerse.",
  "Se ensancha: efectos de red/escala/datos que crecen con el tiempo.", 5),
 ("7. Pista de Reinversión (TAM)", "¿Cuántos años puede reinvertir su caja a altos retornos?",
  "Mercado maduro o saturado: poco espacio para reinvertir bien.",
  "Crecimiento moderado; reinversión parcial a buenos retornos.",
  "TAM amplio y baja penetración: larga pista de reinversión a alto ROIC.", 5),
 ("8. Vientos Seculares", "¿La industria crece o se contrae estructuralmente?",
  "En declive estructural (sustitución, regulación adversa).",
  "Madura / estable, crece en línea con el PIB.",
  "Tendencia secular de crecimiento a su favor durante años.", 5),
 ("9. Riesgo de Disrupción", "¿Qué tan vulnerable es a tecnología, IA o regulación?",
  "Amenaza alta y creíble que podría romper el modelo de negocio.",
  "Amenaza presente pero gestionable; la empresa tiene tiempo de adaptarse.",
  "Baja: el modelo es resistente o la propia empresa lidera el cambio.", 5),
 ("10. Opcionalidad", "¿Tiene vectores de crecimiento con valor no reflejado en el precio?",
  "Depende de un solo producto; sin opcionalidad ni extensiones.",
  "Alguna extensión natural pero incierta.",
  "Varias opciones reales (productos/mercados) que el mercado aún no paga.", 5),
]
r = 14
for c, q, a1, a3, a5, df in blockB:
    qual_row(r, c, q, a1, a3, a5, df)
    r += 1

# Conditional formatting puntajes
for rng in ["F6:F10", "F14:F18"]:
    cu.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=["5"], fill=GREENF))
    cu.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=["3"], fill=AMBF))
    cu.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=["1"], fill=REDF))

# SÍNTESIS
put(cu, "A20", "SÍNTESIS CUALITATIVA", H2, HDRFILL, align="left")
for col in "BCDEFG": put(cu, f"{col}20", "", H2, HDRFILL)
put(cu, "A21", "Puntaje cualitativo (sobre 50)", BOLD, GREYF, align="left")
put(cu, "F21", "=SUM(F6:F10)+SUM(F14:F18)", BOLD, None, '0', "center")
put(cu, "A22", "Equivalente %", BOLD, GREYF, align="left")
put(cu, "F22", "=F21/50", BOLD, None, PCT, "center")
put(cu, "A23", "El negocio HOY (promedio Bloque A)", BOLD, GREYF, align="left")
put(cu, "F23", "=AVERAGE(F6:F10)", BLACK, None, '0.0', "center")
put(cu, "A24", "El FUTURO (promedio Bloque B)", BOLD, GREYF, align="left")
put(cu, "F24", "=AVERAGE(F14:F18)", BLACK, None, '0.0', "center")
put(cu, "A25", "¿La ventaja competitiva hacia adelante…?", BOLD, GREYF, align="left")
put(cu, "B25", '=IF(F24>=4,"Se FORTALECE (foso creciente)",IF(F24>=3,"Se MANTIENE estable",IF(F24>=2,"En riesgo de EROSIÓN","Se EROSIONA — replantear la tesis")))', BOLD, None, None, "left")
cu.merge_cells("B25:E25")
put(cu, "A26", "Veredicto cualitativo global", BOLD, GREYF, align="left")
put(cu, "B26", '=IF(F10=1,"FUERA DEL CÍRCULO DE COMPETENCIA — evitar",IF(F17=1,"RIESGO DE DISRUPCIÓN ALTO — revisar a fondo",IF(F22>=0.8,"Calidad cualitativa EXCELENTE",IF(F22>=0.6,"Calidad cualitativa BUENA",IF(F22>=0.4,"NEUTRO / vigilar","DÉBIL — evitar")))))', BOLD, None, None, "left")
cu.merge_cells("B26:E26")
cu.conditional_formatting.add("B25", FormulaRule(formula=['LEFT(B25,2)="Se"'], fill=GREENF))
cu.conditional_formatting.add("B26", FormulaRule(formula=['OR(ISNUMBER(SEARCH("EXCELENTE",B26)),ISNUMBER(SEARCH("BUENA",B26)))'], fill=GREENF))
cu.conditional_formatting.add("B26", FormulaRule(formula=['OR(ISNUMBER(SEARCH("evitar",B26)),ISNUMBER(SEARCH("DÉBIL",B26)),ISNUMBER(SEARCH("DISRUPCIÓN",B26)))'], fill=REDF))

# TESIS Y RIESGOS (texto libre)
put(cu, "A28", "TESIS Y RIESGOS (texto libre)", H2, HDRFILL, align="left")
for col in "BCDEFG": put(cu, f"{col}28", "", H2, HDRFILL)
free = [
 (29, "Tesis de inversión (¿por qué ganará dinero en 5–10 años?)"),
 (31, "3 riesgos que romperían la tesis"),
 (33, "Señales que me harían VENDER"),
 (35, "Catalizadores / opcionalidad a vigilar"),
]
for row, label in free:
    put(cu, f"A{row}", label, BOLD, GREYF, align="left", wrap=True)
    put(cu, f"B{row}", "", BLUE, YEL, align="left", wrap=True)
    cu.merge_cells(f"B{row}:G{row}")
    cu.row_dimensions[row].height = 46

# Aux contiguo para gráfico radar
put(cu, "A38", "(datos para gráfico radar — no editar)", NOTE, align="left")
radar_names = ["Naturaleza","Moat","P. precios","Directiva","Círculo","Moat futuro","Reinversión","Seculares","Disrupción","Opcionalidad"]
radar_src = ["F6","F7","F8","F9","F10","F14","F15","F16","F17","F18"]
for i, (nm, src) in enumerate(zip(radar_names, radar_src)):
    rr = 39 + i
    put(cu, f"A{rr}", nm, BLACK, None, None, "left")
    put(cu, f"B{rr}", f"={src}", GREEN, None, '0', "center")

# ================= Rúbrica =================
rb = wb.create_sheet("Rúbrica")
rb.sheet_view.showGridLines = False
rb.column_dimensions["A"].width = 42
rb.column_dimensions["B"].width = 14
rb.column_dimensions["C"].width = 12
rb.column_dimensions["D"].width = 8
rb.column_dimensions["E"].width = 10
rb.column_dimensions["F"].width = 58
rb["A1"] = "RÚBRICA QUALITY & COMPOUNDING — PUNTUACIÓN"
rb["A1"].font = H1
rb["A2"] = "Puntaje 0 = Evitar · 1 = Aceptable · 2 = Ideal. Celdas azules = puntaje manual (criterios cualitativos)."
rb["A2"].font = NOTE

# --- Knockouts ---
put(rb, "A4", "PARTE 0 — FILTROS INNEGOCIABLES (KNOCKOUTS)", H2, HDRFILL, align="left")
for col in "BCDEF": put(rb, f"{col}4", "", H2, HDRFILL)
put(rb, "A5", "Criterio", BOLD, GREYF, align="left")
put(rb, "B5", "Valor observado", BOLD, GREYF, align="center")
put(rb, "C5", "Umbral KO", BOLD, GREYF, align="center")
put(rb, "D5", "¿KO?", BOLD, GREYF, align="center")
put(rb, "F5", "Detalle", BOLD, GREYF, align="left")
kos = [
 ("K1. Decrecimiento estructural (ingresos o EPS, CAGR 5a)", "=IFERROR(MIN(Ratios!I5,Ratios!I6),\"\")", "< 0%",
  "=IF(OR(Ratios!I5<0,Ratios!I6<0),\"SÍ\",\"NO\")", PCT, "Revenue o EPS cayendo en tendencia = trampa de valor."),
 ("K2. Deterioro estructural de márgenes (Δ margen bruto 5a)", "=IFERROR(Ratios!F5-Ratios!B5,\"\")", "< -3 pts",
  "=IF(IFERROR(Ratios!F5-Ratios!B5,0)<-0.03,\"SÍ\",\"NO\")", PCT, "Contracción sostenida sin causa transitoria clara."),
 ("K3. ROIC menor que WACC (TTM)", "=IFERROR(Ratios!F12,\"\")", "< WACC",
  "=IF(IFERROR(Ratios!F12,0)<Datos!B22,\"SÍ\",\"NO\")", PCT, "El negocio destruye valor al crecer. Disqualificante."),
 ("K4. Apalancamiento peligroso (Deuda neta/EBITDA)", "=IFERROR(Ratios!F14,\"\")", "> 3.5x",
  "=IF(IFERROR(Ratios!F14,0)>3.5,\"SÍ\",\"NO\")", MULT, "También revisar muro de vencimientos y tasa flotante."),
]
r = 6
for name, val, umb, ko, fmt, det in kos:
    put(rb, f"A{r}", name, BLACK, None, None, "left", wrap=True)
    put(rb, f"B{r}", val, BLACK, None, fmt, "center")
    put(rb, f"C{r}", umb, BLACK, None, None, "center")
    put(rb, f"D{r}", ko, BOLD, None, None, "center")
    put(rb, f"F{r}", det, NOTE, align="left", wrap=True)
    r += 1
put(rb, "A10", "K5. Banderas contables (GAAP vs non-GAAP, caja dudosa, riesgo manipulación)", BLACK, None, None, "left", wrap=True)
put(rb, "B10", "Cualitativo", NOTE, align="center")
put(rb, "C10", "Manual", BLACK, None, None, "center")
put(rb, "D10", "NO", BOLDB, YEL, None, "center")
put(rb, "F10", "Responder SÍ/NO manualmente. Cautela especial con emisores chinos.", NOTE, align="left", wrap=True)
dv_sino = DataValidation(type="list", formula1='"SÍ,NO"', allow_blank=False)
rb.add_data_validation(dv_sino)
dv_sino.add(rb["D10"])
put(rb, "A11", "¿ALGÚN KNOCKOUT ACTIVO?", BOLD, GREYF, align="left")
put(rb, "D11", "=IF(COUNTIF(D6:D10,\"SÍ\")>0,\"SÍ\",\"NO\")", BOLD, None, None, "center")

# --- Calidad ---
put(rb, "A13", "PARTE 1 — CALIDAD (70 puntos)", H2, HDRFILL, align="left")
for col in "BCDEF": put(rb, f"{col}13", "", H2, HDRFILL)
put(rb, "A14", "Criterio", BOLD, GREYF, align="left")
put(rb, "B14", "Valor observado", BOLD, GREYF, align="center")
put(rb, "C14", "Puntaje (0-2)", BOLD, GREYF, align="center")
put(rb, "D14", "Peso", BOLD, GREYF, align="center")
put(rb, "E14", "Puntos", BOLD, GREYF, align="center")
put(rb, "F14", "Guía de puntuación", BOLD, GREYF, align="left")


# tipo: "link" = trae puntaje (0-2) de hoja Cualitativo (escala 1-5 mapeada) · "auto" = fórmula cuantitativa
quality = [
 ("C1. Naturaleza, moat, poder de precios y trayectoria del foso", "link",
  "=IFERROR(AVERAGE(Cualitativo!F6,Cualitativo!F7,Cualitativo!F8,Cualitativo!F14),\"\")", '0.0', 15,
  "=IFERROR((AVERAGE(Cualitativo!F6,Cualitativo!F7,Cualitativo!F8,Cualitativo!F14)-1)/2,0)",
  "Viene de hoja Cualitativo (crit. 1,2,3 + 6 trayectoria). Incluye si el foso se ensancha o erosiona."),
 ("C2. ROIC sostenido (TTM)", "auto", "=IFERROR(Ratios!F12,\"\")", PCT, 15,
  "=IFERROR(IF(Ratios!F12>=0.15,2,IF(Ratios!F12>=0.1,1,0)),0)",
  "2 = ROIC ≥ 15% · 1 = 10–15% · 0 = < 10%. Validar que ROE y ROA se muevan juntos."),
 ("C3. Crecimiento durable (CAGR EPS 5a)", "auto", "=IFERROR(Ratios!I6,\"\")", PCT, 15,
  "=IFERROR(IF(Ratios!I6>=0.12,2,IF(Ratios!I6>=0.08,1,0)),0)",
  "2 = ≥ 12% con pista larga · 1 = 8–12% visible · 0 = < 8%. Mirar también la foto forward."),
 ("C4. Pista de reinversión, vientos seculares y opcionalidad", "link",
  "=IFERROR(AVERAGE(Cualitativo!F15,Cualitativo!F16,Cualitativo!F18),\"\")", '0.0', 10,
  "=IFERROR((AVERAGE(Cualitativo!F15,Cualitativo!F16,Cualitativo!F18)-1)/2,0)",
  "Viene de hoja Cualitativo (crit. 7,8,10). Mide cuántos años puede reinvertir a alto retorno."),
 ("C5. Calidad de márgenes (Δ margen EBITDA 5a)", "auto", "=IFERROR(Ratios!F6-Ratios!B6,\"\")", PCT, 5,
  "=IFERROR(IF(Ratios!F6-Ratios!B6>=0.01,2,IF(Ratios!F6-Ratios!B6>=-0.01,1,0)),0)",
  "2 = expansión ≥ +1 pt · 1 = estable (±1 pt) · 0 = contracción"),
 ("C6. Balance y supervivencia (DN/EBITDA)", "auto", "=IFERROR(Ratios!F14,\"\")", MULT, 5,
  "=IFERROR(IF(Ratios!F14<=2,2,IF(Ratios!F14<=3.5,1,0)),0)",
  "2 = caja neta o ≤ 2x · 1 = 2x–3.5x con flujo estable · 0 = > 3.5x"),
 ("C7. Dirección (skin in the game) y círculo de competencia", "link",
  "=IFERROR(AVERAGE(Cualitativo!F9,Cualitativo!F10),\"\")", '0.0', 5,
  "=IFERROR((AVERAGE(Cualitativo!F9,Cualitativo!F10)-1)/2,0)",
  "Viene de hoja Cualitativo (crit. 4,5). Incluye si TÚ entiendes el negocio."),
]
r = 15
for name, tipo, val, vfmt, peso, score, guia in quality:
    put(rb, f"A{r}", name, BLACK, None, None, "left", wrap=True)
    bfont = GREEN if tipo == "link" else BLACK
    put(rb, f"B{r}", val, bfont, None, vfmt, "center")
    cfont = GREEN if tipo == "link" else BLACK
    put(rb, f"C{r}", score, cfont, None, '0.0', "center")
    put(rb, f"D{r}", peso, BLACK, None, '0', "center")
    put(rb, f"E{r}", f"=IFERROR(C{r}/2*D{r},0)", BLACK, None, '0.0', "center")
    put(rb, f"F{r}", guia, NOTE, align="left", wrap=True)
    r += 1
# quality rows 15..21
put(rb, "A22", "Subtotal CALIDAD", BOLD, GREYF, align="left")
put(rb, "D22", "=SUM(D15:D21)", BOLD, GREYF, '0', "center")
put(rb, "E22", "=SUM(E15:E21)", BOLD, GREYF, '0.0', "center")

# --- Valoración ---
put(rb, "A24", "PARTE 2 — VALORACIÓN COMO GUARDARRAÍL (30 puntos)", H2, HDRFILL, align="left")
for col in "BCDEF": put(rb, f"{col}24", "", H2, HDRFILL)
put(rb, "A25", "Criterio", BOLD, GREYF, align="left")
put(rb, "B25", "Valor observado", BOLD, GREYF, align="center")
put(rb, "C25", "Puntaje (0-2)", BOLD, GREYF, align="center")
put(rb, "D25", "Peso", BOLD, GREYF, align="center")
put(rb, "E25", "Puntos", BOLD, GREYF, align="center")
put(rb, "F25", "Guía de puntuación", BOLD, GREYF, align="left")
valuation = [
 ("V1. Fwd P/E vs. mediana propia 5a (ratio)", "=IFERROR(Ratios!G17/Ratios!I7,\"\")", '0.00', 8,
  "=IFERROR(IF(Ratios!G17/Ratios!I7<=1,2,IF(Ratios!G17/Ratios!I7<=1.3,1,0)),0)",
  "2 = ≤ 1.0 (en o bajo su mediana) · 1 = ≤ 1.3 (premium moderado justificado) · 0 = > 1.3"),
 ("V2. PEG forward", "=IFERROR(Ratios!I10,\"\")", '0.00', 8,
  "=IFERROR(IF(Ratios!I10<=1.5,2,IF(Ratios!I10<=2,1,0)),0)",
  "2 = ≤ 1.5 · 1 = ≤ 2.0 (laxo: se paga calidad) · 0 = > 2.0"),
 ("V3. EV/EBITDA TTM vs. mediana propia y sector", "=IFERROR(Ratios!F18,\"\")", MULT, 7,
  "=IFERROR(IF(AND(Ratios!F18<=Ratios!I8,Ratios!F18<=Comparables!E14),2,IF(OR(Ratios!F18<=Ratios!I8,Ratios!F18<=Comparables!E14),1,0)),0)",
  "2 = por debajo de ambas referencias · 1 = por debajo de una · 0 = por encima de ambas"),
 ("V4. FCF Yield NTM (ajustado)", "=IFERROR(Ratios!G20,\"\")", PCT, 7,
  "=IFERROR(IF(Ratios!G20>=0.04,2,IF(Ratios!G20>=0.02,1,0)),0)",
  "2 = ≥ 4% · 1 = 2–4% (o bajo pero justificado por reinversión a alto ROIC: ajustar manualmente) · 0 = < 2%"),
]
r = 26
for name, val, vfmt, peso, score, guia in valuation:
    put(rb, f"A{r}", name, BLACK, None, None, "left", wrap=True)
    put(rb, f"B{r}", val, BLACK, None, vfmt, "center")
    put(rb, f"C{r}", score, BLACK, None, '0', "center")
    put(rb, f"D{r}", peso, BLACK, None, '0', "center")
    put(rb, f"E{r}", f"=IFERROR(C{r}/2*D{r},0)", BLACK, None, '0.0', "center")
    put(rb, f"F{r}", guia, NOTE, align="left", wrap=True)
    r += 1
# valuation rows 26..29
put(rb, "A30", "Subtotal VALORACIÓN", BOLD, GREYF, align="left")
put(rb, "D30", "=SUM(D26:D29)", BOLD, GREYF, '0', "center")
put(rb, "E30", "=SUM(E26:E29)", BOLD, GREYF, '0.0', "center")

# --- Resultado ---
put(rb, "A32", "PARTE 3 — RESULTADO", H2, HDRFILL, align="left")
for col in "BCDEF": put(rb, f"{col}32", "", H2, HDRFILL)
put(rb, "A33", "Puntaje total (sobre 100)", BOLD, GREYF, align="left")
put(rb, "B33", "=E22+E30", BOLD, None, '0.0', "center")
put(rb, "A34", "Puntaje %", BOLD, GREYF, align="left")
put(rb, "B34", "=B33/100", BOLD, None, PCT, "center")
put(rb, "A35", "CLASIFICACIÓN", BOLD, GREYF, align="left")
# La clasificación va envuelta en (...) y se le concatena un matiz de momentum cuando el TTM YoY
# (ingresos o EPS) es negativo. NO cambia el puntaje; los rótulos CF usan LEFT() sobre el prefijo, intacto.
put(rb, "B35",
 '=(IF(D11="SÍ","NO APTO (KNOCKOUT)",'
 'IF(OR(Cualitativo!F10=1,Cualitativo!F17=1),"REVISAR — riesgo cualitativo alto",'
 'IF(AND(B34>=0.75,C15>=1.5),"COMPOUNDER DE CONVICCIÓN",'
 'IF(B34>=0.55,"CALIDAD EN OBSERVACIÓN","NO APTO")))))'
 '&IF(OR(IFERROR(Ratios!F8,0)<0,IFERROR(Ratios!F9,0)<0)," (con desaceleración reciente — vigilar)","")',
 BOLD, None, None, "center")
rb.merge_cells("B35:F35")
put(rb, "A36", "Regla", NOTE, align="left")
put(rb, "B36", "Compounder: ≥75%, moat fuerte (C1≥1.5) y sin KO ni riesgo cualitativo alto · Observación: ≥55% sin KO · Revisar: círculo de competencia o disrupción en nivel 1 · No apto: <55% o cualquier KO · El titular añade '(con desaceleración reciente — vigilar)' si el momentum TTM YoY es negativo, sin alterar el puntaje.", NOTE, align="left", wrap=True)
rb.merge_cells("B36:F36")

# Conditional formatting
rb.conditional_formatting.add("C15:C21", FormulaRule(formula=["C15>=1.5"], fill=GREENF))
rb.conditional_formatting.add("C15:C21", FormulaRule(formula=["AND(C15>=0.75,C15<1.5)"], fill=AMBF))
rb.conditional_formatting.add("C15:C21", FormulaRule(formula=["C15<0.75"], fill=REDF))
for op, val, fill in [("equal", "2", GREENF), ("equal", "1", AMBF), ("equal", "0", REDF)]:
    rb.conditional_formatting.add("C26:C29", CellIsRule(operator=op, formula=[val], fill=fill))
rb.conditional_formatting.add("D6:D11", FormulaRule(formula=['D6="SÍ"'], fill=REDF))
rb.conditional_formatting.add("D6:D11", FormulaRule(formula=['D6="NO"'], fill=GREENF))
rb.conditional_formatting.add("B35", FormulaRule(formula=['LEFT(B35,10)="COMPOUNDER"'], fill=GREENF))
rb.conditional_formatting.add("B35", FormulaRule(formula=['LEFT(B35,7)="CALIDAD"'], fill=AMBF))
rb.conditional_formatting.add("B35", FormulaRule(formula=['OR(LEFT(B35,2)="NO",LEFT(B35,7)="REVISAR")'], fill=REDF))

# --- Parte 4: momentum reciente (NO es knockout duro; visibiliza y baja la confianza) ---
# C3 y K1 usan CAGR a 5 años y esconden frenazos recientes; esto los compensa con el YoY del TTM.
put(rb, "A38", "PARTE 4 — MOMENTUM RECIENTE (TTM YoY) · no es knockout, ajusta la confianza", H2, HDRFILL, align="left")
for col in "BCDEF": put(rb, f"{col}38", "", H2, HDRFILL)
put(rb, "A39", "Crecimiento ingresos TTM YoY", BLACK, None, None, "left", wrap=True)
put(rb, "B39", '=IFERROR(Ratios!F8,"")', BLACK, None, PCT, "center")
put(rb, "F39", "TTM vs. último año fiscal. Negativo = ventas desacelerando ahora mismo.", NOTE, align="left", wrap=True)
put(rb, "A40", "Crecimiento EPS TTM YoY", BLACK, None, None, "left", wrap=True)
put(rb, "B40", '=IFERROR(Ratios!F9,"")', BLACK, None, PCT, "center")
put(rb, "F40", "Captura caídas recientes que el CAGR a 5 años (C3/K1) esconde.", NOTE, align="left", wrap=True)
put(rb, "A41", "BANDERA DE MOMENTUM", BOLD, GREYF, align="left")
put(rb, "B41", '=IF(OR(IFERROR(Ratios!F8,0)<0,IFERROR(Ratios!F9,0)<0),"DESACELERACIÓN RECIENTE — revisar la tesis","Sin alerta de momentum")', BOLD, None, None, "left")
rb.merge_cells("B41:F41")
put(rb, "A42", "Confianza en la clasificación", BOLD, GREYF, align="left")
put(rb, "B42", '=IF(OR(IFERROR(Ratios!F8,0)<0,IFERROR(Ratios!F9,0)<0),"REDUCIDA","Normal")', BOLD, None, None, "center")
rb.conditional_formatting.add("B41", FormulaRule(formula=['ISNUMBER(SEARCH("DESACELERA",B41))'], fill=AMBF))
rb.conditional_formatting.add("B41", FormulaRule(formula=['ISNUMBER(SEARCH("Sin alerta",B41))'], fill=GREENF))
rb.conditional_formatting.add("B42", FormulaRule(formula=['B42="REDUCIDA"'], fill=AMBF))
rb.conditional_formatting.add("B42", FormulaRule(formula=['B42="Normal"'], fill=GREENF))

# ================= Valoración =================
vl = wb.create_sheet("Valoración")
vl.sheet_view.showGridLines = False
vl.column_dimensions["A"].width = 46
vl.column_dimensions["B"].width = 16
vl.column_dimensions["C"].width = 60
vl["A1"] = "VALORACIÓN — ¿PRECIO RAZONABLE, CARO O BARATO?"
vl["A1"].font = H1
vl["A2"] = ("Ancla de múltiplo NORMALIZADA (mediana recortada vs. techo por crecimiento, la MENOR) para no anclarse a "
           "años de hipercrecimiento. Doble método (P/E y FCF Yield); la conclusión titular toma el MÁS CONSERVADOR.")
vl["A2"].font = NOTE

put(vl, "A4", "ENTRADAS", H2, HDRFILL, align="left")
put(vl, "B4", "", H2, HDRFILL); put(vl, "C4", "", H2, HDRFILL)
vrows = [
 ("Precio actual de mercado ($)", "=Datos!B23", PRICE, GREEN, "Vinculado a Datos!B23"),
 ("EPS NTM proyectado ($)", "=Datos!G10", PRICE, GREEN, "Vinculado a Datos!G10"),
 ("Mediana P/E 5a CRUDA (referencia)", "=Ratios!I7", MULT, GREEN, "Solo referencia; suele inflarse con años de hipercrecimiento"),
 ("Mediana P/E RECORTADA (excluye el máximo)", '=IFERROR((SMALL(Ratios!B17:F17,2)+SMALL(Ratios!B17:F17,3))/2,"")', MULT, BLACK, "Mediana de los 5 P/E históricos quitando el más alto (robusta a picos)"),
 ("Crecimiento EPS normalizado (%)", '=IFERROR(MIN(Ratios!I6,Ratios!I12),"")', PCT, BLACK, "MIN(CAGR EPS 5a, crec. EPS NTM): evita que un repunte desde base baja infle el techo"),
]
r = 5
for name, f, fmt, fnt, nota in vrows:
    put(vl, f"A{r}", name, BOLD, GREYF, align="left")
    put(vl, f"B{r}", f, fnt, None, fmt, "right")
    put(vl, f"C{r}", nota, NOTE, align="left")
    r += 1
put(vl, "A10", "PEG objetivo para techo de múltiplo", BOLD, GREYF, align="left")
put(vl, "B10", 2.0, BLUE, YEL, '0.00', "right")
put(vl, "C10", "Techo de P/E justificable = PEG objetivo × crecimiento normalizado (laxo: se paga calidad)", NOTE, align="left", wrap=True)
put(vl, "A11", "Techo P/E justificado por crecimiento", BOLD, GREYF, align="left")
put(vl, "B11", '=IFERROR(B10*B9*100,"")', BLACK, None, MULT, "right")
put(vl, "C11", "Múltiplo máximo que el crecimiento esperado justifica", NOTE, align="left")
put(vl, "A12", "ANCLA DE MÚLTIPLO (la menor)", BOLD, GREYF, align="left")
put(vl, "B12", '=IFERROR(MIN(B8,B11),"")', BOLDB, YEL, MULT, "right")
put(vl, "C12", "Fórmula: MÍN(mediana recortada, techo por crecimiento). Base de la valoración por P/E", NOTE, align="left", wrap=True)
put(vl, "A13", "Factor P/E objetivo BAJO (× ancla)", BOLD, GREYF, align="left")
put(vl, "B13", 0.90, BLUE, YEL, '0.00', "right")
put(vl, "C13", "0.90 = exigir un 10% de descuento vs. la ancla", NOTE, align="left")
put(vl, "A14", "Factor P/E objetivo ALTO (× ancla)", BOLD, GREYF, align="left")
put(vl, "B14", 1.10, BLUE, YEL, '0.00', "right")
put(vl, "C14", "1.10 = tolerar un premium del 10% si la calidad lo justifica", NOTE, align="left")
put(vl, "A15", "Margen de seguridad deseado (%)", BOLD, GREYF, align="left")
put(vl, "B15", 0.15, BLUE, YEL, PCT, "right")
put(vl, "C15", "Descuento exigido sobre el valor justo para el rango de compra", NOTE, align="left")
put(vl, "A16", "FCF Yield objetivo (chequeo cruzado, %)", BOLD, GREYF, align="left")
put(vl, "B16", 0.04, BLUE, YEL, PCT, "right")
put(vl, "C16", "4% por defecto; relajar para compounders que reinvierten a alto ROIC", NOTE, align="left")

put(vl, "A18", "VALOR JUSTO (método P/E sobre ancla normalizada)", H2, HDRFILL, align="left")
put(vl, "B18", "", H2, HDRFILL); put(vl, "C18", "", H2, HDRFILL)
put(vl, "A19", "Valor justo BAJO ($)", BOLD, GREYF, align="left")
put(vl, "B19", '=IFERROR(B6*B12*B13,"")', BLACK, None, PRICE, "right")
put(vl, "C19", "Fórmula: EPS NTM × ancla × factor bajo", NOTE, align="left")
put(vl, "A20", "Valor justo ALTO ($)", BOLD, GREYF, align="left")
put(vl, "B20", '=IFERROR(B6*B12*B14,"")', BLACK, None, PRICE, "right")
put(vl, "C20", "Fórmula: EPS NTM × ancla × factor alto", NOTE, align="left")
put(vl, "A21", "Valor justo MEDIO ($)", BOLD, GREYF, align="left")
put(vl, "B21", '=IFERROR(AVERAGE(B19:B20),"")', BLACK, None, PRICE, "right")

put(vl, "A23", "CHEQUEO CRUZADO (método FCF Yield)", H2, HDRFILL, align="left")
put(vl, "B23", "", H2, HDRFILL); put(vl, "C23", "", H2, HDRFILL)
put(vl, "A24", "EV implícito ($mm) = FCF aj. NTM / yield objetivo", BOLD, GREYF, align="left")
put(vl, "B24", '=IFERROR(Datos!G14/B16,"")', BLACK, None, MONEY, "right")
put(vl, "A25", "Valor por acción implícito ($)", BOLD, GREYF, align="left")
put(vl, "B25", '=IFERROR((B24-(Datos!G16-Datos!G15))/Datos!G11,"")', BLACK, None, PRICE, "right")
put(vl, "C25", "Fórmula: (EV implícito − deuda neta NTM) / acciones diluidas NTM", NOTE, align="left")

put(vl, "A27", "BANDERA DE DISCREPANCIA ENTRE MÉTODOS", H2, HDRFILL, align="left")
put(vl, "B27", "", H2, HDRFILL); put(vl, "C27", "", H2, HDRFILL)
put(vl, "A28", "Diferencia P/E vs. FCF (%)", BOLD, GREYF, align="left")
put(vl, "B28", '=IFERROR(ABS(B21/B25-1),"")', BLACK, None, PCT, "right")
put(vl, "A29", "¿Divergencia > 25%?", BOLD, GREYF, align="left")
put(vl, "B29", '=IF(IFERROR(ABS(B21/B25-1),0)>0.25,"SÍ — los métodos no concuerdan; predomina el más conservador","NO — métodos alineados")', BOLD, None, None, "left")
vl.merge_cells("B29:C29")
put(vl, "A30", "VALOR JUSTO CONSERVADOR (titular) ($)", BOLD, GREYF, align="left")
put(vl, "B30", '=IFERROR(MIN(B21,B25),"")', BOLDB, YEL, PRICE, "right")
put(vl, "C30", "El MENOR entre el valor medio por P/E y el del chequeo por FCF Yield", NOTE, align="left", wrap=True)

put(vl, "A32", "CONCLUSIÓN", H2, HDRFILL, align="left")
put(vl, "B32", "", H2, HDRFILL); put(vl, "C32", "", H2, HDRFILL)
put(vl, "A33", "¿Precio actual razonable, caro o barato?", BOLD, GREYF, align="left")
put(vl, "B33", '=IFERROR(IF(B5<=B30*(1-B15),"BARATO",IF(B5<=B30*(1+B15),"RAZONABLE","CARO")),"")', BOLD, None, None, "center")
put(vl, "C33", "Medido contra el valor justo CONSERVADOR (método más prudente de los dos)", NOTE, align="left", wrap=True)
put(vl, "A34", "Prima / (descuento) vs. valor justo conservador", BOLD, GREYF, align="left")
put(vl, "B34", '=IFERROR(B5/B30-1,"")', BLACK, None, PCT, "right")
put(vl, "A35", "RANGO IDEAL DE COMPRA — desde ($)", BOLD, GREYF, align="left")
put(vl, "B35", '=IFERROR(B30*(1-B15),"")', BOLD, GREENF, PRICE, "right")
put(vl, "C35", "Fórmula: valor justo conservador × (1 − margen de seguridad)", NOTE, align="left")
put(vl, "A36", "RANGO IDEAL DE COMPRA — hasta ($)", BOLD, GREYF, align="left")
put(vl, "B36", '=IFERROR(B30,"")', BOLD, GREENF, PRICE, "right")
put(vl, "C36", "Hasta el valor justo conservador (comprar por debajo de él, idealmente con margen)", NOTE, align="left")
put(vl, "A38", "Nota: si la Rúbrica clasifica como Compounder de Convicción y el precio cae dentro o bajo el rango sin cambio en fundamentales, la caída es oportunidad de acumular, no señal de venta. Revisa también la BANDERA DE MOMENTUM (Rúbrica) antes de concluir.", NOTE, align="left", wrap=True)
vl.merge_cells("A38:C38")
vl.row_dimensions[38].height = 42

vl.conditional_formatting.add("B33", FormulaRule(formula=['B33="BARATO"'], fill=GREENF))
vl.conditional_formatting.add("B33", FormulaRule(formula=['B33="RAZONABLE"'], fill=AMBF))
vl.conditional_formatting.add("B33", FormulaRule(formula=['B33="CARO"'], fill=REDF))
vl.conditional_formatting.add("B29", FormulaRule(formula=['ISNUMBER(SEARCH("no concuerdan",B29))'], fill=AMBF))
vl.conditional_formatting.add("B29", FormulaRule(formula=['ISNUMBER(SEARCH("alineados",B29))'], fill=GREENF))

# ================= Gráficos =================
g = wb.create_sheet("Gráficos")
g.sheet_view.showGridLines = False
g["A1"] = "GRÁFICOS DINÁMICOS — se actualizan al cambiar Datos / Comparables"
g["A1"].font = H1

def line_chart(title, rows, anchor, y_title, pct=True):
    ch = LineChart()
    ch.title = title
    ch.style = 2
    ch.height = 8.5
    ch.width = 17
    ch.y_axis.title = y_title
    cats = Reference(rt, min_col=2, max_col=7, min_row=4, max_row=4)
    for rw in rows:
        data = Reference(rt, min_col=1, max_col=7, min_row=rw, max_row=rw)
        ch.add_data(data, titles_from_data=True, from_rows=True)
    ch.set_categories(cats)
    if pct:
        ch.y_axis.numFmt = "0%"
    for s in ch.series:
        s.smooth = False
    g.add_chart(ch, anchor)

line_chart("Márgenes (%) — tendencia 5a + proyección", [5, 6, 7], "A3", "Margen")
line_chart("Rentabilidad sobre capital — ROE / ROA / ROIC", [10, 11, 12], "J3", "Retorno")
line_chart("Crecimiento YoY — Ingresos vs. EPS", [8, 9], "A21", "Crecimiento")

ch4 = LineChart()
ch4.title = "Múltiplos de valoración — P/E y EV/EBITDA vs. historia"
ch4.style = 2
ch4.height = 8.5
ch4.width = 17
ch4.y_axis.title = "Múltiplo (x)"
cats = Reference(rt, min_col=2, max_col=7, min_row=4, max_row=4)
for rw in (17, 18):
    ch4.add_data(Reference(rt, min_col=1, max_col=7, min_row=rw, max_row=rw), titles_from_data=True, from_rows=True)
ch4.set_categories(cats)
for s in ch4.series: s.smooth = False
g.add_chart(ch4, "J21")

bar = BarChart()
bar.type = "col"
bar.title = "COMPARADOR DINÁMICO — métrica elegida en Comparables!B19"
bar.style = 10
bar.height = 8.5
bar.width = 17
data = Reference(cp, min_col=2, max_col=5, min_row=22, max_row=22)
cats2 = Reference(cp, min_col=2, max_col=5, min_row=21, max_row=21)
bar.add_data(data, titles_from_data=False, from_rows=True)
bar.set_categories(cats2)
bar.legend = None
g.add_chart(bar, "A39")

bar2 = BarChart()
bar2.type = "col"
bar2.title = f"ROIC (TTM) — {COMPANY_SHORT} vs. competidores vs. sector"
bar2.style = 11
bar2.height = 8.5
bar2.width = 17
data2 = Reference(cp, min_col=2, max_col=5, min_row=10, max_row=10)
bar2.add_data(data2, titles_from_data=False, from_rows=True)
bar2.set_categories(cats2)
bar2.legend = None
bar2.y_axis.numFmt = "0%"
g.add_chart(bar2, "J39")

from openpyxl.chart import RadarChart
radar = RadarChart()
radar.type = "filled"
radar.style = 12
radar.title = "Perfil cualitativo (1–5) — Hoy (1-5) + Futuro (6-10)"
radar.height = 11
radar.width = 14
rdata = Reference(cu, min_col=2, min_row=39, max_row=48)
rcats = Reference(cu, min_col=1, min_row=39, max_row=48)
radar.add_data(rdata, titles_from_data=False)
radar.set_categories(rcats)
radar.legend = None
g.add_chart(radar, "A57")

wb.save(ARGS.out)
print("OK")
