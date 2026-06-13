"""
db.py -- Helpers para obtener conexiones a SQLite desde cualquier modulo.
"""

import sqlite3
from config import DB_PATH


def get_db() -> sqlite3.Connection:
    """Retorna una conexion con row_factory y foreign keys activos.

    WAL + busy_timeout permiten lecturas concurrentes con una escritura y
    evitan errores 'database is locked' cuando varios clientes empujan
    resultados al mismo tiempo (sync en vivo).
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn
