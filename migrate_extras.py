"""
migrate_extras.py — Agrega columnas de predicciones extra a la tabla usuarios.
Idempotente: no falla si ya existen.
Correr: python migrate_extras.py
"""
from db import get_db

NUEVAS_COLUMNAS = [
    ("goleador_mundial",    "TEXT"),
    ("equipo_mas_goleador", "TEXT"),
    ("equipo_sorpresa",     "TEXT"),
    ("equipo_decepcion",    "TEXT"),
]

def migrar():
    with get_db() as conn:
        existentes = {r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()}
        for col, tipo in NUEVAS_COLUMNAS:
            if col not in existentes:
                conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
                print(f"  + columna '{col}' agregada")
            else:
                print(f"  ✓ columna '{col}' ya existe")
        conn.commit()
    print("Migración completada.")

if __name__ == "__main__":
    migrar()
