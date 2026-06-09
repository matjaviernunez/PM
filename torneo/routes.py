"""
torneo/routes.py — Página de Torneo: posiciones de grupos + cruces 16avos.
"""

import json, os
from flask import Blueprint, render_template
from flask_login import login_required

from game.bracket import get_todas_tablas, get_cruces_16avos
from config import GRUPOS, BASE_DIR

torneo_bp = Blueprint("torneo", __name__,
                      template_folder="../templates/torneo")


def _equipos_map() -> dict:
    path = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m = {}
    for equipos in data["grupos"].values():
        for e in equipos:
            m[e["codigo"]] = {"nombre": e["nombre"], "iso": e["iso"]}
    return m

EQUIPOS = _equipos_map()


@torneo_bp.route("/")
@login_required
def index():
    tablas  = get_todas_tablas()
    cruces  = get_cruces_16avos()

    return render_template(
        "torneo/index.html",
        tablas=tablas,
        cruces=cruces,
        grupos=GRUPOS,
        equipos=EQUIPOS,
        tab_activa="posiciones",
    )


@torneo_bp.route("/16avos")
@login_required
def dieciseisavos():
    tablas = get_todas_tablas()
    cruces = get_cruces_16avos()

    return render_template(
        "torneo/index.html",
        tablas=tablas,
        cruces=cruces,
        grupos=GRUPOS,
        equipos=EQUIPOS,
        tab_activa="16avos",
    )
