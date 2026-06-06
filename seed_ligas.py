"""seed_ligas.py — Crea las ligas iniciales."""
from db import get_db

LIGAS = ["Liga Principal", "Todos contra todos"]


def seed():
    with get_db() as conn:
        for nombre in LIGAS:
            conn.execute("INSERT OR IGNORE INTO ligas (nombre) VALUES (?)", (nombre,))
        conn.commit()
    print("✓ Ligas creadas")


if __name__ == "__main__":
    seed()
