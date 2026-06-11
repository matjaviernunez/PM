"""
auth/routes.py — Rutas de registro, login y logout.
"""

import json
import logging
import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, session as flask_session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from auth.models import Usuario
from db import get_db
from config import BASE_DIR

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

# ── Helpers ────────────────────────────────────────────────────────────────

def _cargar_equipos():
    """Retorna lista de {codigo, nombre, emoji} para los selectores."""
    path = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    equipos = []
    for grupo, lista in data["grupos"].items():
        for e in lista:
            equipos.append(e)
    return sorted(equipos, key=lambda e: e["nombre"])

def _cargar_ligas():
    with get_db() as conn:
        rows = conn.execute("SELECT id, nombre FROM ligas ORDER BY nombre").fetchall()
    return [dict(r) for r in rows]


# ── Registro ───────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    equipos = _cargar_equipos()
    ligas   = _cargar_ligas()

    if request.method == "POST":
        username         = request.form.get("username", "").strip()
        password         = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        nickname         = request.form.get("nickname", "").strip() or username
        edad             = request.form.get("edad") or None
        equipo_favorito  = request.form.get("equipo_favorito") or None
        jugador_favorito = request.form.get("jugador_favorito", "").strip() or None
        campeon_favorito = request.form.get("campeon_favorito") or None
        liga_ids         = request.form.getlist("ligas")  # puede ser múltiple

        # Validaciones
        if not username:
            flash("El usuario es obligatorio.", "error")
        elif not password:
            flash("La contraseña es obligatoria.", "error")
        elif password != password_confirm:
            flash("Las contraseñas no coinciden.", "error")
        elif len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        elif Usuario.get_by_username(username):
            flash("Ese nombre de usuario ya está en uso.", "error")
        else:
            liga_ids = [int(lid) for lid in liga_ids if lid]
            password_hash = generate_password_hash(password)
            usuario = Usuario.crear(
                username=username,
                password_hash=password_hash,
                nickname=nickname,
                edad=int(edad) if edad else None,
                equipo_favorito=equipo_favorito,
                jugador_favorito=jugador_favorito,
                campeon_favorito=campeon_favorito,
                liga_ids=liga_ids if liga_ids else None,
            )
            login_user(usuario)
            flash(f"¡Bienvenido, {usuario.nickname}! 🎉", "success")
            return redirect(url_for("index"))

    return render_template("auth/register.html", equipos=equipos, ligas=ligas)


# ── Login ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        usuario = Usuario.get_by_username(username)
        if not usuario or not check_password_hash(usuario.password_hash, password):
            flash("Usuario o contraseña incorrectos.", "error")
        else:
            login_user(usuario, remember=True)

            # ── Popup de ranking ─────────────────────────────────────────
            try:
                from game.scoring import get_ranking
                from db import get_db

                # Liga de referencia: primera privada (no "todos"), o general
                ligas_u       = usuario.ligas()
                ligas_privadas = [l for l in ligas_u if 'todos' not in l['nombre'].lower()]
                liga_ref_id   = ligas_privadas[0]['id'] if ligas_privadas else (ligas_u[0]['id'] if ligas_u else None)

                tabla   = get_ranking(liga_id=liga_ref_id)
                total   = len(tabla)
                mi_pos  = next((i + 1 for i, j in enumerate(tabla) if j['usuario_id'] == usuario.id), None)

                if mi_pos is not None:
                    prev_pos = usuario.ultima_posicion
                    if prev_pos is not None and prev_pos != mi_pos:
                        delta = prev_pos - mi_pos  # positivo = subió
                        if mi_pos == 1:
                            msg = "👑 ¡Eres el primero! Disfrútalo mientras dure 😏"
                        elif delta > 0 and prev_pos == total:
                            msg = f"🎉 ¡Ya no eres el colero! Ahora vas {mi_pos}° — algo es algo ¿no? 😄"
                        elif delta > 0:
                            msg = f"🚀 ¡Subiste {delta} puesto{'s' if delta > 1 else ''}! Ahora vas {mi_pos}°"
                        elif mi_pos == total:
                            msg = "💀 ¡Te fuiste al fondo! Último... pero aún hay tiempo 😅"
                        elif prev_pos == 1:
                            msg = "😤 ¡Te bajaron del trono! Eso no puede quedar así"
                        else:
                            msg = f"📉 Bajaste {abs(delta)} puesto{'s' if abs(delta) > 1 else ''}, ahora vas {mi_pos}°. ¡A despertar!"
                        flask_session['ranking_popup'] = msg

                    # Actualizar posición guardada
                    with get_db() as conn:
                        conn.execute("UPDATE usuarios SET ultima_posicion = ? WHERE id = ?",
                                     (mi_pos, usuario.id))
                        conn.commit()
            except Exception as _e:
                logging.getLogger(__name__).warning('Ranking popup error: %s', _e)
            # ─────────────────────────────────────────────────────────────

            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

    return render_template("auth/login.html")


# ── Perfil ─────────────────────────────────────────────────────────────────

@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    equipos = _cargar_equipos()
    ligas   = _cargar_ligas()

    if request.method == "POST":
        edad             = request.form.get("edad") or None
        equipo_favorito      = request.form.get("equipo_favorito") or None
        jugador_favorito     = request.form.get("jugador_favorito", "").strip() or None
        campeon_favorito     = request.form.get("campeon_favorito") or None
        goleador_mundial     = request.form.get("goleador_mundial", "").strip() or None
        equipo_mas_goleador  = request.form.get("equipo_mas_goleador") or None
        equipo_sorpresa      = request.form.get("equipo_sorpresa") or None
        equipo_decepcion     = request.form.get("equipo_decepcion") or None
        liga_ids             = [int(lid) for lid in request.form.getlist("ligas") if lid]

        Usuario.actualizar(
            user_id=current_user.id,
            edad=int(edad) if edad else None,
            equipo_favorito=equipo_favorito,
            jugador_favorito=jugador_favorito,
            campeon_favorito=campeon_favorito,
            goleador_mundial=goleador_mundial,
            equipo_mas_goleador=equipo_mas_goleador,
            equipo_sorpresa=equipo_sorpresa,
            equipo_decepcion=equipo_decepcion,
            nuevas_liga_ids=liga_ids if liga_ids else None,
        )
        # Refrescar datos del usuario en sesión
        from flask_login import login_user
        usuario_actualizado = Usuario.get_by_id(current_user.id)
        login_user(usuario_actualizado)
        flash("Perfil actualizado ✓", "success")
        return redirect(url_for("auth.perfil"))

    ligas_usuario = {l["id"] for l in current_user.ligas()}

    # ── Historial personal ────────────────────────────────────────────────
    from db import get_db
    historial = {}
    with get_db() as conn:
        # Stats generales
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN pr.puntos_obtenidos > 0 THEN 1 ELSE 0 END) AS con_puntos,
                SUM(pr.puntos_obtenidos) AS puntos_total,
                SUM(CASE WHEN pa.goles_local IS NOT NULL
                    AND pr.goles_local = pa.goles_local
                    AND pr.goles_visita = pa.goles_visita THEN 1 ELSE 0 END) AS exactos
            FROM predicciones pr
            JOIN partidos pa ON pa.id = pr.partido_id
            WHERE pr.usuario_id = ? AND pa.abierto = 0
        """, (current_user.id,)).fetchone()
        historial["stats"] = dict(stats) if stats else {}

        # Evolución de puntos por fecha (para gráfico)
        evo = conn.execute("""
            SELECT pa.fecha, SUM(pr.puntos_obtenidos) AS pts_dia
            FROM predicciones pr
            JOIN partidos pa ON pa.id = pr.partido_id
            WHERE pr.usuario_id = ? AND pa.abierto = 0 AND pr.puntos_obtenidos IS NOT NULL
            GROUP BY pa.fecha
            ORDER BY pa.fecha
        """, (current_user.id,)).fetchall()
        # Acumular puntos
        acum = 0
        evolucion = []
        for r in evo:
            acum += (r["pts_dia"] or 0)
            evolucion.append({"fecha": r["fecha"], "puntos": acum})
        historial["evolucion"] = evolucion

        # Top 3 mejores predicciones
        top = conn.execute("""
            SELECT pa.equipo_local AS local, pa.equipo_visita AS visita,
                   pa.fecha, pa.fase,
                   pr.goles_local, pr.goles_visita, pr.puntos_obtenidos
            FROM predicciones pr
            JOIN partidos pa ON pa.id = pr.partido_id
            WHERE pr.usuario_id = ? AND pa.abierto = 0 AND pr.puntos_obtenidos IS NOT NULL
            ORDER BY pr.puntos_obtenidos DESC
            LIMIT 3
        """, (current_user.id,)).fetchall()
        historial["top"] = [dict(r) for r in top]

    return render_template("auth/perfil.html", equipos=equipos, ligas=ligas,
                           ligas_usuario=ligas_usuario, historial=historial)


# ── Logout ─────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
