"""
auth/models.py — Modelo de usuario compatible con Flask-Login.
Accede directamente a SQLite sin ORM.
"""

import random
import string
from flask_login import UserMixin
from db import get_db


def _generar_codigo(username: str) -> str:
    """Genera un código único tipo ABC-jav para identificar al jugador."""
    letras = ''.join(random.choices(string.ascii_uppercase, k=3))
    sufijo = username[:3].upper()
    return f"{letras}-{sufijo}"


class Usuario(UserMixin):
    def __init__(self, row):
        self.id               = row["id"]
        self.username         = row["username"]
        self.password_hash    = row["password_hash"]
        self.nickname         = row["nickname"]
        self.edad             = row["edad"]
        self.equipo_favorito  = row["equipo_favorito"]
        self.jugador_favorito = row["jugador_favorito"]
        self.campeon_favorito = row["campeon_favorito"]
        self.codigo           = row["codigo"]
        self.es_admin         = bool(row["es_admin"])
        self.created_at       = row["created_at"]

    def get_id(self):
        return str(self.id)

    # ── Ligas del usuario ──────────────────────────────────────────────────
    def ligas(self):
        with get_db() as conn:
            rows = conn.execute("""
                SELECT l.id, l.nombre
                FROM ligas l
                JOIN usuario_liga ul ON ul.liga_id = l.id
                WHERE ul.usuario_id = ?
            """, (self.id,)).fetchall()
        return [dict(r) for r in rows]

    # ── Queries estáticas ──────────────────────────────────────────────────
    @staticmethod
    def get_by_id(user_id: int):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE id = ?", (user_id,)
            ).fetchone()
        return Usuario(row) if row else None

    @staticmethod
    def get_by_username(username: str):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE username = ?", (username,)
            ).fetchone()
        return Usuario(row) if row else None

    @staticmethod
    def crear(username, password_hash, nickname, edad=None,
              equipo_favorito=None, jugador_favorito=None,
              campeon_favorito=None, liga_ids=None):
        codigo = _generar_codigo(username)
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO usuarios
                    (username, password_hash, nickname, edad,
                     equipo_favorito, jugador_favorito, campeon_favorito, codigo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, password_hash, nickname, edad,
                  equipo_favorito, jugador_favorito, campeon_favorito, codigo))
            user_id = cur.lastrowid

            if liga_ids:
                conn.executemany(
                    "INSERT OR IGNORE INTO usuario_liga (usuario_id, liga_id) VALUES (?, ?)",
                    [(user_id, lid) for lid in liga_ids]
                )
            conn.commit()
        return Usuario.get_by_id(user_id)

    @staticmethod
    def todos():
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM usuarios ORDER BY created_at DESC"
            ).fetchall()
        return [Usuario(r) for r in rows]
