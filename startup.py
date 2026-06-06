"""
startup.py — Corre antes de arrancar el servidor.
Inicializa la DB y hace seed de datos base si está vacía.
"""

import os
from init_db import init_db
from seed_ligas import seed as seed_ligas
from seed_partidos import seed as seed_partidos


def main():
    print("▶ Inicializando base de datos...")
    init_db()

    # Solo hacer seed si no hay partidos aún
    from db import get_db
    with get_db() as conn:
        n_partidos = conn.execute("SELECT COUNT(*) FROM partidos").fetchone()[0]
        n_ligas    = conn.execute("SELECT COUNT(*) FROM ligas").fetchone()[0]

    if n_partidos == 0:
        print("▶ Seeding partidos...")
        seed_partidos()

    if n_ligas == 0:
        print("▶ Seeding ligas...")
        seed_ligas()

    print("✓ Startup completo")


if __name__ == "__main__":
    main()
