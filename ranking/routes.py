"""
ranking/routes.py — Tabla de posiciones general y por liga.
"""

import json, os
from flask import Blueprint, render_template, request
from flask_login import login_required

from game.scoring import get_ranking
from db import get_db
from config import FASES, BASE_DIR

ranking_bp = Blueprint("ranking", __name__,
                       template_folder="../templates/ranking")


def _equipos_iso():
    path = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m = {}
    for equipos in data["grupos"].values():
        for e in equipos:
            m[e["codigo"]] = e["iso"]
    return m


@ranking_bp.route("/")
@login_required
def index():
    with get_db() as conn:
        ligas = conn.execute(
            "SELECT id, nombre FROM ligas ORDER BY nombre"
        ).fetchall()

        # Distribución de campeón favorito
        campeon_stats = conn.execute("""
            SELECT campeon_favorito AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE campeon_favorito IS NOT NULL
            GROUP BY campeon_favorito
            ORDER BY votos DESC
            LIMIT 12
        """).fetchall()

        # Marcadores más predichos
        marcadores_stats = conn.execute("""
            SELECT goles_local, goles_visita, COUNT(*) AS total
            FROM predicciones
            GROUP BY goles_local, goles_visita
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

    liga_id    = request.args.get("liga", type=int)
    tabla      = get_ranking(liga_id=liga_id)
    equipos_iso = _equipos_iso()

    return render_template(
        "ranking/index.html",
        tabla=tabla,
        ligas=[dict(l) for l in ligas],
        liga_id=liga_id,
        fases=FASES,
        campeon_stats=[dict(r) for r in campeon_stats],
        marcadores_stats=[dict(r) for r in marcadores_stats],
        equipos_iso=equipos_iso,
    )
