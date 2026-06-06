"""
admin/routes.py — Panel de administrador.
Solo accesible para usuarios con es_admin = TRUE.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps

import json, os
from db import get_db
from game.scoring import recalcular_partido
from config import GRUPOS, BASE_DIR

def _equipos_map():
    path = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m = {}
    for equipos in data["grupos"].values():
        for e in equipos:
            m[e["codigo"]] = {"nombre": e["nombre"], "iso": e["iso"]}
    return m

EQUIPOS = _equipos_map()

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            flash("Acceso restringido.", "error")
            return redirect(url_for("predicciones.index"))
        return f(*args, **kwargs)
    return decorated


# ── Panel principal ────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
@admin_required
def index():
    with get_db() as conn:
        # Partidos sin resultado, ordenados por fecha
        pendientes = conn.execute("""
            SELECT * FROM partidos
            WHERE goles_local IS NULL
            ORDER BY fecha, hora
        """).fetchall()

        # Partidos con resultado ya cargado
        completados = conn.execute("""
            SELECT * FROM partidos
            WHERE goles_local IS NOT NULL
            ORDER BY fecha DESC, hora DESC
            LIMIT 20
        """).fetchall()

        usuarios = conn.execute(
            "SELECT id, nickname, username, es_admin, created_at FROM usuarios ORDER BY created_at DESC"
        ).fetchall()

        ligas = conn.execute("SELECT * FROM ligas ORDER BY nombre").fetchall()

    return render_template(
        "admin/index.html",
        pendientes=[dict(p) for p in pendientes],
        completados=[dict(p) for p in completados],
        usuarios=[dict(u) for u in usuarios],
        ligas=[dict(l) for l in ligas],
        grupos=GRUPOS,
        equipos=EQUIPOS,
    )


# ── Cargar resultado de un partido ─────────────────────────────────────────

@admin_bp.route("/resultado", methods=["POST"])
@login_required
@admin_required
def cargar_resultado():
    data         = request.get_json()
    partido_id   = data.get("partido_id")
    goles_local  = data.get("goles_local")
    goles_visita = data.get("goles_visita")

    if partido_id is None or goles_local is None or goles_visita is None:
        return jsonify({"ok": False, "error": "Datos incompletos"}), 400

    with get_db() as conn:
        conn.execute("""
            UPDATE partidos
            SET goles_local = ?, goles_visita = ?, abierto = FALSE
            WHERE id = ?
        """, (int(goles_local), int(goles_visita), int(partido_id)))
        conn.commit()

    procesadas = recalcular_partido(int(partido_id))
    return jsonify({"ok": True, "predicciones_procesadas": procesadas})


# ── Abrir / cerrar partido ─────────────────────────────────────────────────

@admin_bp.route("/toggle-partido", methods=["POST"])
@login_required
@admin_required
def toggle_partido():
    data       = request.get_json()
    partido_id = data.get("partido_id")
    abierto    = data.get("abierto")

    with get_db() as conn:
        conn.execute(
            "UPDATE partidos SET abierto = ? WHERE id = ?",
            (bool(abierto), int(partido_id))
        )
        conn.commit()
    return jsonify({"ok": True})


# ── Eliminar usuario ───────────────────────────────────────────────────────

@admin_bp.route("/eliminar-usuario", methods=["POST"])
@login_required
@admin_required
def eliminar_usuario():
    data       = request.get_json()
    usuario_id = data.get("usuario_id")

    if int(usuario_id) == current_user.id:
        return jsonify({"ok": False, "error": "No puedes eliminarte a ti mismo"}), 400

    with get_db() as conn:
        conn.execute("DELETE FROM predicciones  WHERE usuario_id = ?", (usuario_id,))
        conn.execute("DELETE FROM puntajes_fase WHERE usuario_id = ?", (usuario_id,))
        conn.execute("DELETE FROM usuario_liga  WHERE usuario_id = ?", (usuario_id,))
        conn.execute("DELETE FROM usuarios      WHERE id = ?",         (usuario_id,))
        conn.commit()
    return jsonify({"ok": True})


# ── Crear liga ─────────────────────────────────────────────────────────────

@admin_bp.route("/crear-liga", methods=["POST"])
@login_required
@admin_required
def crear_liga():
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("El nombre de la liga no puede estar vacío.", "error")
        return redirect(url_for("admin.index"))
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO ligas (nombre) VALUES (?)", (nombre,))
        conn.commit()
    flash(f"Liga '{nombre}' creada.", "success")
    return redirect(url_for("admin.index"))


# ── Predicciones de un partido (para admin) ───────────────────────────────

@admin_bp.route("/predicciones-partido/<int:partido_id>")
@login_required
@admin_required
def predicciones_partido(partido_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.*, u.nickname
            FROM predicciones p
            JOIN usuarios u ON u.id = p.usuario_id
            WHERE p.partido_id = ?
            ORDER BY u.nickname
        """, (partido_id,)).fetchall()
    return jsonify({"predicciones": [dict(r) for r in rows]})


# ── Predicciones de un usuario (para admin) ───────────────────────────────

@admin_bp.route("/predicciones-usuario/<int:usuario_id>")
@login_required
@admin_required
def predicciones_usuario(usuario_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.*, pa.equipo_local, pa.equipo_visita,
                   pa.goles_local AS real_local, pa.goles_visita AS real_visita,
                   pa.fase, pa.grupo
            FROM predicciones p
            JOIN partidos pa ON pa.id = p.partido_id
            WHERE p.usuario_id = ?
            ORDER BY pa.fecha, pa.hora
        """, (usuario_id,)).fetchall()

        total = conn.execute("""
            SELECT COALESCE(SUM(puntos), 0) as total
            FROM puntajes_fase WHERE usuario_id = ?
        """, (usuario_id,)).fetchone()["total"]

    return jsonify({
        "predicciones": [dict(r) for r in rows],
        "total_puntos": total,
    })


# ── Borrar una predicción individual ──────────────────────────────────────

@admin_bp.route("/borrar-prediccion", methods=["POST"])
@login_required
@admin_required
def borrar_prediccion():
    data       = request.get_json()
    usuario_id = data.get("usuario_id")
    partido_id = data.get("partido_id")

    with get_db() as conn:
        # Restar los puntos que tenía antes de borrar
        pred = conn.execute("""
            SELECT puntos_obtenidos FROM predicciones
            WHERE usuario_id = ? AND partido_id = ?
        """, (usuario_id, partido_id)).fetchone()

        if pred and pred["puntos_obtenidos"]:
            fase = conn.execute(
                "SELECT fase FROM partidos WHERE id = ?", (partido_id,)
            ).fetchone()["fase"]
            conn.execute("""
                UPDATE puntajes_fase SET puntos = MAX(0, puntos - ?)
                WHERE usuario_id = ? AND fase = ?
            """, (pred["puntos_obtenidos"], usuario_id, fase))

        conn.execute("""
            DELETE FROM predicciones WHERE usuario_id = ? AND partido_id = ?
        """, (usuario_id, partido_id))
        conn.commit()

    return jsonify({"ok": True})


# ── Scraper manual ────────────────────────────────────────────────────────

@admin_bp.route("/scrape", methods=["POST"])
@login_required
@admin_required
def scrape():
    from scraper.runner import scrape_resultados
    resultado = scrape_resultados()
    return jsonify(resultado)


# ── Hacerse admin (solo primera vez via CLI) ───────────────────────────────

@admin_bp.route("/make-admin/<int:usuario_id>", methods=["POST"])
@login_required
@admin_required
def make_admin(usuario_id):
    with get_db() as conn:
        conn.execute("UPDATE usuarios SET es_admin = TRUE WHERE id = ?", (usuario_id,))
        conn.commit()
    return jsonify({"ok": True})
