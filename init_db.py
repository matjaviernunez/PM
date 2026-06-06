"""
init_db.py — Inicializa la base de datos SQLite del Mundial 2026.
Idempotente: se puede correr múltiples veces sin borrar datos existentes.

Uso:
    python init_db.py
"""

import sqlite3
import os
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ── Ligas ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ligas (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    # ── Usuarios ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            nickname        TEXT NOT NULL,
            edad            INTEGER,
            equipo_favorito TEXT,
            jugador_favorito TEXT,
            campeon_favorito TEXT,
            codigo          TEXT UNIQUE NOT NULL,
            es_admin        BOOLEAN DEFAULT FALSE,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Usuario ↔ Liga (many-to-many) ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuario_liga (
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            liga_id    INTEGER NOT NULL REFERENCES ligas(id)    ON DELETE CASCADE,
            PRIMARY KEY (usuario_id, liga_id)
        )
    """)

    # ── Partidos ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fase          TEXT NOT NULL,
            grupo         TEXT,
            fecha         DATE,
            hora          TIME,
            equipo_local  TEXT NOT NULL,
            equipo_visita TEXT NOT NULL,
            goles_local   INTEGER,
            goles_visita  INTEGER,
            penales_ganador TEXT,
            abierto       BOOLEAN DEFAULT TRUE
        )
    """)

    # ── Predicciones ───────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predicciones (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id       INTEGER NOT NULL REFERENCES usuarios(id),
            partido_id       INTEGER NOT NULL REFERENCES partidos(id),
            goles_local      INTEGER NOT NULL,
            goles_visita     INTEGER NOT NULL,
            penales_ganador  TEXT,
            puntos_obtenidos INTEGER,
            UNIQUE(usuario_id, partido_id)
        )
    """)

    # ── Puntajes acumulados por fase ───────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS puntajes_fase (
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            fase       TEXT NOT NULL,
            puntos     INTEGER DEFAULT 0,
            PRIMARY KEY (usuario_id, fase)
        )
    """)

    # ── Goleadores ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goleadores (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador TEXT NOT NULL,
            equipo  TEXT NOT NULL,
            goles   INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Tarjetas ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tarjetas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador   TEXT NOT NULL,
            equipo    TEXT NOT NULL,
            amarillas INTEGER DEFAULT 0,
            rojas     INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Índices ────────────────────────────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_predicciones_usuario ON predicciones(usuario_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_predicciones_partido ON predicciones(partido_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_partidos_fase       ON partidos(fase)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_partidos_fecha      ON partidos(fecha)")

    # ── Liga por defecto ───────────────────────────────────────────────────
    cur.execute("INSERT OR IGNORE INTO ligas (nombre) VALUES ('Todos contra todos')")

    conn.commit()
    conn.close()
    print(f"✓ Base de datos inicializada en: {DB_PATH}")


if __name__ == "__main__":
    init_db()
