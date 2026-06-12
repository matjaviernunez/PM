"""
migrate_estado.py — Añade columna `estado` a la tabla partidos.
Valores: 'pre' (no ha empezado), 'in' (en juego), 'post' (terminado).
"""
from db import get_db

def run():
    with get_db() as conn:
        # Verificar si la columna ya existe
        cols = [row[1] for row in conn.execute("PRAGMA table_info(partidos)").fetchall()]
        if 'estado' in cols:
            print("Columna 'estado' ya existe — nada que hacer.")
            return

        conn.execute("ALTER TABLE partidos ADD COLUMN estado TEXT DEFAULT 'pre'")

        # Partidos con abierto=FALSE ya empezaron — marcarlos según si tienen resultado
        conn.execute("""
            UPDATE partidos
            SET estado = CASE
                WHEN goles_local IS NOT NULL THEN 'post'
                ELSE 'in'
            END
            WHERE abierto = FALSE
        """)
        conn.commit()
        print("Migración completada: columna 'estado' añadida.")

if __name__ == '__main__':
    run()
