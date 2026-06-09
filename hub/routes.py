"""
hub/routes.py — Página de información del Mundial 2026.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from db import get_db

hub_bp = Blueprint("hub", __name__, template_folder="../templates/hub")


@hub_bp.route("/")
@login_required
def index():
    with get_db() as conn:
        goleadores = conn.execute("""
            SELECT jugador, equipo, goles
            FROM goleadores
            ORDER BY goles DESC
            LIMIT 20
        """).fetchall()

        tarjetas = conn.execute("""
            SELECT jugador, equipo, amarillas, rojas
            FROM tarjetas
            ORDER BY rojas DESC, amarillas DESC
            LIMIT 20
        """).fetchall()

    return render_template(
        "hub/index.html",
        goleadores=[dict(r) for r in goleadores],
        tarjetas=[dict(r) for r in tarjetas],
    )
