#!/usr/bin/env python3
"""Llena las celdas de entrada de la rúbrica desde un JSON y recalcula.

Uso:
    python fill_rubrica.py <archivo.xlsx> <valores.json> [--no-recalc]

El JSON tiene la forma {"Hoja": {"Celda": valor, ...}, ...}. Solo escribe;
no cambia formato ni fórmulas. Ejemplo:
    {"Datos": {"B5": 257637, "C5": 282836},
     "Comparables": {"C5": 0.14, "C8": 0.16},
     "Cualitativo": {"F6": 5, "F7": 3, "G6": "Marca dominante; ver 10-K Item 1"}}
Recalcula al final con el script oficial de xlsx (busca recalc.py).
"""
import sys, json, subprocess, os
from openpyxl import load_workbook

def main():
    if len(sys.argv) < 3:
        print("Uso: python fill_rubrica.py <archivo.xlsx> <valores.json> [--no-recalc]")
        sys.exit(1)
    xlsx, js = sys.argv[1], sys.argv[2]
    do_recalc = "--no-recalc" not in sys.argv
    data = json.load(open(js, encoding="utf-8"))
    wb = load_workbook(xlsx)
    written = 0
    for sheet, cells in data.items():
        if sheet not in wb.sheetnames:
            print(f"AVISO: hoja '{sheet}' no existe, se omite")
            continue
        ws = wb[sheet]
        for cell, value in cells.items():
            ws[cell] = value          # conserva formato/estilo previo de la celda
            written += 1
    wb.save(xlsx)
    print(f"Escritas {written} celdas en {xlsx}")

    if do_recalc:
        for path in ("/mnt/skills/public/xlsx/scripts/recalc.py",
                     os.path.join(os.path.dirname(__file__), "recalc.py")):
            if os.path.exists(path):
                subprocess.run([sys.executable, path, xlsx, "60"])
                return
        print("AVISO: no se encontró recalc.py; abre el archivo en Excel para recalcular.")

if __name__ == "__main__":
    main()
