"""
Script de auditoria: filas historicas con valores no-SOLO en campos SOLO.

Ejecutar desde v2/:
    python audit_solo_contamination.py

Produce un resumen en stdout y guarda un CSV en analytics/reports/.

Contexto: antes del commit P0.2, exam_responses.solo_level recibia los
valores "excelente"/"insuficiente" (etiqueta de correccion de opcion
multiple), y exam_results.predominant_solo_level recibia un valor
inventado desde el porcentaje de aciertos ("relacional" o "multiestructural").
Ninguno de esos valores pertenece al conjunto de cinco niveles SOLO de Biggs
y Collis (1982).

Este script cuenta cuantas filas estan afectadas para documentarlo en el
articulo (dato 5 de la seccion "Lo que este trabajo produce para el articulo").
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Agregar app/ al path para importar modelos
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text

SQLITE_PATH = os.environ.get("SQLITE_PATH", "./data/rag_system.db")
REPORTS_DIR = Path("./analytics/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

VALID_SOLO_LEVELS = {
    "preestructural", "uniestructural", "multiestructural",
    "relacional", "abstracto_extendido",
}

NON_SOLO_VALUES = {"excelente", "bueno", "insuficiente", "regular"}


def run_audit():
    engine = create_engine(f"sqlite:///{SQLITE_PATH}")

    with engine.connect() as conn:
        # --- exam_responses.solo_level ---
        rows_er = conn.execute(
            text("SELECT id, exam_id, user_id, solo_level FROM exam_responses WHERE solo_level IS NOT NULL")
        ).fetchall()

        contaminated_er = [
            r for r in rows_er
            if r.solo_level not in VALID_SOLO_LEVELS
        ]
        total_er = len(rows_er)
        contam_er = len(contaminated_er)

        # --- exam_results.predominant_solo_level ---
        rows_res = conn.execute(
            text("SELECT id, exam_id, user_id, predominant_solo_level FROM exam_results WHERE predominant_solo_level IS NOT NULL")
        ).fetchall()

        contaminated_res = [
            r for r in rows_res
            if r.predominant_solo_level not in VALID_SOLO_LEVELS
        ]
        total_res = len(rows_res)
        contam_res = len(contaminated_res)

    # Imprimir resumen
    print("=" * 60)
    print("AUDITORIA: valores no-SOLO en campos SOLO")
    print(f"Fecha: {datetime.now().isoformat()}")
    print("=" * 60)

    print(f"\nexam_responses.solo_level")
    print(f"  Filas con valor no-NULL:        {total_er}")
    print(f"  Filas con valor no-SOLO:        {contam_er}")
    pct_er = (contam_er / total_er * 100) if total_er else 0
    print(f"  Porcentaje contaminado:         {pct_er:.1f}%")

    if contaminated_er:
        # Distribucion de valores encontrados
        from collections import Counter
        dist = Counter(r.solo_level for r in contaminated_er)
        print(f"  Valores encontrados:            {dict(dist)}")

    print(f"\nexam_results.predominant_solo_level")
    print(f"  Filas con valor no-NULL:        {total_res}")
    print(f"  Filas con valor no-SOLO:        {contam_res}")
    pct_res = (contam_res / total_res * 100) if total_res else 0
    print(f"  Porcentaje contaminado:         {pct_res:.1f}%")

    if contaminated_res:
        from collections import Counter
        dist2 = Counter(r.predominant_solo_level for r in contaminated_res)
        print(f"  Valores encontrados:            {dict(dist2)}")

    print("\nNota: los datos nuevos (post-commit P0.2) tienen solo_level=NULL.")
    print("Estos conteos aplican solo al historico acumulado antes de ese commit.")

    # Guardar CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = REPORTS_DIR / f"solo_audit_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tabla", "campo", "total_no_null", "contaminadas", "pct", "valores_encontrados"])
        writer.writerow([
            "exam_responses", "solo_level", total_er, contam_er,
            f"{pct_er:.1f}",
            str(dict(Counter(r.solo_level for r in contaminated_er))) if contaminated_er else "",
        ])
        writer.writerow([
            "exam_results", "predominant_solo_level", total_res, contam_res,
            f"{pct_res:.1f}",
            str(dict(Counter(r.predominant_solo_level for r in contaminated_res))) if contaminated_res else "",
        ])

    print(f"\nCSV guardado en: {csv_path}")
    return {"exam_responses": contam_er, "exam_results": contam_res}


if __name__ == "__main__":
    run_audit()
