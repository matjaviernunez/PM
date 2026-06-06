"""
predicciones/routes.py — Vista principal de predicciones por fecha.
"""

import json, os
from datetime import date
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from game.models import (
    get_todos_partidos_grupos,
    get_predicciones_usuario,
    guardar_prediccion,
    guardar_predicciones_lote,
    cerrar_partidos_vencidos,
)
from config import GRUPOS, BASE_DIR

pred_bp = Blueprint("predicciones", __name__,
                    template_folder="../templates/predicciones")

NOMBRES_DIAS = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
    "Sunday": "Domingo",
}

NOMBRES_MESES = {
    1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun",
    7:"jul", 8:"ago", 9:"sep", 10:"oct", 11:"nov", 12:"dic",
}

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


def _formato_fecha(fecha_str: str) -> str:
    """'2026-06-11' → 'Jueves 11 jun'"""
    try:
        d = date.fromisoformat(fecha_str)
        dia_en = d.strftime("%A")
        return f"{NOMBRES_DIAS.get(dia_en, dia_en)} {d.day} {NOMBRES_MESES[d.month]}"
    except Exception:
        return fecha_str


# ── Vista principal ────────────────────────────────────────────────────────

@pred_bp.route("/")
@pred_bp.route("/grupos")
@login_required
def index():
    cerrar_partidos_vencidos()

    partidos = get_todos_partidos_grupos()
    partido_ids = [p["id"] for p in partidos]
    predicciones = get_predicciones_usuario(current_user.id, partido_ids)

    # Agrupar por fecha
    por_fecha = {}
    for p in partidos:
        por_fecha.setdefault(p["fecha"], []).append(p)

    # Fechas formateadas
    fechas_label = {f: _formato_fecha(f) for f in por_fecha}

    # Día de hoy para highlight
    hoy = date.today().isoformat()

    return render_template(
        "predicciones/index.html",
        por_fecha=por_fecha,
        fechas_label=fechas_label,
        predicciones=predicciones,
        equipos=EQUIPOS,
        grupos=GRUPOS,
        hoy=hoy,
    )


# ── Guardar lote (un día entero) ───────────────────────────────────────────

@pred_bp.route("/guardar-lote", methods=["POST"])
@login_required
def guardar_lote():
    data = request.get_json()
    items = data.get("predicciones", [])

    if not items:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    resultado = guardar_predicciones_lote(current_user.id, items)
    return jsonify({"ok": True, **resultado})


# ── Guardar individual (AJAX) ──────────────────────────────────────────────

@pred_bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    data = request.get_json()
    partido_id   = data.get("partido_id")
    goles_local  = data.get("goles_local")
    goles_visita = data.get("goles_visita")

    if partido_id is None or goles_local is None or goles_visita is None:
        return jsonify({"ok": False, "error": "Datos incompletos"}), 400

    ok = guardar_prediccion(
        usuario_id=current_user.id,
        partido_id=int(partido_id),
        goles_local=int(goles_local),
        goles_visita=int(goles_visita),
    )
    return jsonify({"ok": ok, "error": "Partido cerrado" if not ok else None})


# ── Vista semana (redirige a index) ───────────────────────────────────────

@pred_bp.route("/semana")
@login_required
def semana():
    from flask import redirect, url_for
    return redirect(url_for("predicciones.index"))
