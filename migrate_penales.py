"""
migrate_penales.py -- Agrega columnas penales_local / penales_visita
a las tablas predicciones y partidos.

Uso:
    python migrate_penales.py
"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from config import DB_PATH

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cols_pred = [r[1] for r in cur.execute("PRAGMA table_info(predicciones)").fetchall()]
    cols_part = [r[1] for r in cur.execute("PRAGMA table_info(partidos)").fetchall()]

    changes = []
    if "penales_local"  not in cols_pred:
        cur.execute("ALTER TABLE predicciones ADD COLUMN penales_local  INTEGER")
        changes.append("predicciones.penales_local")
    if "penales_visita" not in cols_pred:
        cur.execute("ALTER TABLE predicciones ADD COLUMN penales_visita INTEGER")
        changes.append("predicciones.penales_visita")
    if "penales_local"  not in cols_part:
        cur.execute("ALTER TABLE partidos ADD COLUMN penales_local  INTEGER")
        changes.append("partidos.penales_local")
    if "penales_visita" not in cols_part:
        cur.execute("ALTER TABLE partidos ADD COLUMN penales_visita INTEGER")
        changes.append("partidos.penales_visita")

    conn.commit()
    conn.close()

    if changes:
        for c in changes:
            print(f"  + {c}")
        print("Migracion completada.")
    else:
        print("Ya estaba al dia, nada que migrar.")

if __name__ == "__main__":
    run()
