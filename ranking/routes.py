"""
ranking/routes.py — Tabla de posiciones general y por liga.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required

from game.scoring import get_ranking
from db import get_db
from config import FASES

ranking_bp = Blueprint("ranking", __name__,
                       template_folder="../templates/ranking")


@ranking_bp.route("/")
@login_required
def index():
    # Cargar ligas para el filtro
    with get_db() as conn:
        ligas = conn.execute(
            "SELECT id, nombre FROM ligas ORDER BY nombre"
        ).fetchall()

    liga_id = request.args.get("liga", type=int)
    tabla   = get_ranking(liga_id=liga_id)

    return render_template(
        "ranking/index.html",
        tabla=tabla,
        ligas=[dict(l) for l in ligas],
        liga_id=liga_id,
        fases=FASES,
    )
