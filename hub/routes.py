"""
hub/routes.py — Página de información del Mundial 2026.
"""

from flask import Blueprint, render_template, request, jsonify
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


# ── Sync de estadisticas (goleadores/tarjetas) desde el cliente ────────────
# El navegador agrega desde el scoreboard de ESPN y envia el total aqui.
# Reemplaza ambas tablas. Solo reemplaza si llegan datos (no borra con vacio).

@hub_bp.route("/push-stats", methods=["POST"])
@login_required
def push_stats():
    data = request.get_json(silent=True) or {}
    gol = data.get("goleadores", [])
    tar = data.get("tarjetas", [])

    def _int(x):
        try:
            return max(0, int(x))
        except (ValueError, TypeError):
            return 0

    gol_rows = [
        ((g.get("jugador") or "").strip(), (g.get("equipo") or "").strip(), _int(g.get("goles")))
        for g in gol if (g.get("jugador") or "").strip()
    ]
    tar_rows = [
        ((t.get("jugador") or "").strip(), (t.get("equipo") or "").strip(),
         _int(t.get("amarillas")), _int(t.get("rojas")))
        for t in tar if (t.get("jugador") or "").strip()
    ]

    with get_db() as conn:
        if gol_rows:
            conn.execute("DELETE FROM goleadores")
            conn.executemany(
                "INSERT INTO goleadores (jugador, equipo, goles) VALUES (?, ?, ?)", gol_rows
            )
        if tar_rows:
            conn.execute("DELETE FROM tarjetas")
            conn.executemany(
                "INSERT INTO tarjetas (jugador, equipo, amarillas, rojas) VALUES (?, ?, ?, ?)", tar_rows
            )
        conn.commit()

    return jsonify({"ok": True, "goleadores": len(gol_rows), "tarjetas": len(tar_rows)})
