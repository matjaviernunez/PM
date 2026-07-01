"""
torneo/routes.py — Página de Torneo: posiciones de grupos + cruces eliminatorias.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from db import get_db

from game.bracket import get_todas_tablas, get_cruces_16avos, get_cruces_proyectados
from game.models import get_partidos_eliminatorias, get_fases_eliminatorias_disponibles, get_fase_activa
from config import GRUPOS, EQUIPOS

torneo_bp = Blueprint("torneo", __name__,
                      template_folder="../templates/torneo")


# Etiquetas bonitas para cada fase
_LABEL_FASE = {
    "16avos": "16avos",
    "octavos": "Octavos",
    "cuartos": "Cuartos",
    "semis": "Semis",
    "3er_puesto": "3er Puesto",
    "final": "Final",
}


@torneo_bp.route("/")
@login_required
def index():
    tab = request.args.get("tab") or get_fase_activa()

    tablas = get_todas_tablas()
    cruces = get_cruces_16avos()

    # Fases knockout con partidos en DB
    fases_ko = get_fases_eliminatorias_disponibles()
    todos_ko = get_partidos_eliminatorias()
    partidos_ko = {}
    for p in todos_ko:
        partidos_ko.setdefault(p["fase"], []).append(dict(p))

    # Orden cronológico dentro de cada fase (necesario para mapeo posicional del bracket)
    for fase in partidos_ko:
        partidos_ko[fase].sort(key=lambda p: (p.get("fecha", ""), p.get("hora", "")))

    return render_template(
        "torneo/index.html",
        tablas=tablas,
        cruces=cruces,
        cruces_proyectados=get_cruces_proyectados(),
        grupos=GRUPOS,
        equipos=EQUIPOS,
        tab_activa=tab,
        fases_ko=fases_ko,
        partidos_ko=partidos_ko,
        label_fase=_LABEL_FASE,
    )


# -- Cierre automatico de cruces de 16avos (sin boton) ----------
# El cliente trae de ESPN los cruces reales (equipos ya definidos) y los envia
# aqui. Candados: (1) la fase de grupos debe estar completa, (2) idempotente,
# (3) solo acepta codigos de equipos reales. Asi no se puede corromper el cuadro.

@torneo_bp.route("/cerrar-cruces", methods=["POST"])
@login_required
def cerrar_cruces():
    data = request.get_json(silent=True) or {}
    partidos = data.get("partidos", [])
    validos = set(EQUIPOS.keys())

    with get_db() as conn:
        # (1) la fase de grupos debe estar 100% completa
        faltan = conn.execute(
            "SELECT COUNT(*) FROM partidos WHERE fase = 'grupos' AND goles_local IS NULL"
        ).fetchone()[0]
        if faltan > 0:
            return jsonify({"ok": False, "error": "Fase de grupos no terminada",
                            "faltan": faltan}), 409

        # (2) idempotente: si ya hay 16avos, no recrear
        ya = conn.execute(
            "SELECT COUNT(*) FROM partidos WHERE fase = '16avos'"
        ).fetchone()[0]
        if ya > 0:
            return jsonify({"ok": True, "ya_fijado": True, "creados": 0})

        # (3) solo equipos reales (en equipos.json); requiere los 16 partidos
        limpios = []
        for pr in partidos:
            home = (pr.get("home") or "").strip()
            away = (pr.get("away") or "").strip()
            if home in validos and away in validos and home != away:
                limpios.append((home, away,
                                (pr.get("fecha") or "").strip(),
                                (pr.get("hora") or "").strip()))
        if len(limpios) < 16:
            return jsonify({"ok": False, "error": "Cruces incompletos o con placeholders",
                            "validos": len(limpios)}), 400

        for home, away, fecha, hora in limpios:
            conn.execute("""
                INSERT INTO partidos
                    (fase, grupo, fecha, hora, equipo_local, equipo_visita, abierto, estado)
                VALUES ('16avos', NULL, ?, ?, ?, ?, 1, 'pre')
            """, (fecha, hora, home, away))
        conn.commit()

    return jsonify({"ok": True, "creados": len(limpios)})
