"""
auth/routes.py — Rutas de registro, login y logout.
"""

import json
import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
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
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

    return render_template("auth/login.html")


# ── Logout ─────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
