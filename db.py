"""
db.py — Helpers para obtener conexiones a SQLite desde cualquier módulo.
"""

import sqlite3
from config import DB_PATH


def get_db() -> sqlite3.Connection:
    """Retorna una conexión con row_factory y foreign keys activos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
