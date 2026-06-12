"""
ranking/routes.py — Tabla de posiciones general y por liga.

Sincronización de resultados: el cliente (JS) hace el fetch a ESPN
y envía los datos al endpoint /ranking/push-scores. Esto evita el
proxy de PythonAnywhere que bloquea llamadas salientes a ESPN.
"""

import json, os
from flask import Blueprint, render_template, request, jsonify, Response, abort
from flask_login import login_required, current_user

from game.scoring import get_ranking, recalcular_partido
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


@ranking_bp.route("/push-scores", methods=["POST"])
@login_required
def push_scores():
    """
    Recibe desde el cliente los resultados del scoreboard de ESPN,
    actualiza partidos en DB y recalcula puntos.
    Body JSON: { "events": [ {home, away, home_score, away_score, state, fecha_ect}, ... ] }
    """
    data = request.get_json(silent=True) or {}
    events = data.get("events", [])

    actualizados = 0
    recalculados = 0

    with get_db() as conn:
        for ev in events:
            home_abbr  = ev.get("home", "")
            away_abbr  = ev.get("away", "")
            home_score = ev.get("home_score")
            away_score = ev.get("away_score")
            state      = ev.get("state", "")
            fecha_ect  = ev.get("fecha_ect", "")

            if not home_abbr or not away_abbr:
                continue
            if home_score is None or away_score is None:
                continue

            try:
                gl = int(home_score)
                gv = int(away_score)
            except (ValueError, TypeError):
                continue

            # Buscar partido en DB
            if fecha_ect:
                partido = conn.execute("""
                    SELECT id, goles_local, goles_visita, estado
                    FROM partidos
                    WHERE equipo_local = ? AND equipo_visita = ? AND fecha = ?
                """, (home_abbr, away_abbr, fecha_ect)).fetchone()
            else:
                partido = conn.execute("""
                    SELECT id, goles_local, goles_visita, estado
                    FROM partidos
                    WHERE equipo_local = ? AND equipo_visita = ?
                """, (home_abbr, away_abbr)).fetchone()

            if not partido:
                continue

            # Nunca sobreescribir un partido ya marcado como 'post' en DB.
            # Evita que datos cacheados/viejos de ESPN corrompan el resultado final.
            if partido["estado"] == "post":
                continue

            # Solo actualizar si el marcador cambió
            if partido["goles_local"] == gl and partido["goles_visita"] == gv:
                continue

            conn.execute("""
                UPDATE partidos SET goles_local = ?, goles_visita = ?
                WHERE id = ?
            """, (gl, gv, partido["id"]))
            conn.commit()
            actualizados += 1

            recalcular_partido(partido["id"])
            recalculados += 1

    return jsonify({"ok": True, "actualizados": actualizados, "recalculados": recalculados})


@ranking_bp.route("/")
@login_required
def index():
    with get_db() as conn:
        ligas = conn.execute(
            "SELECT id, nombre FROM ligas ORDER BY nombre"
        ).fetchall()

        campeon_stats = conn.execute("""
            SELECT campeon_favorito AS equipo, COUNT(*) AS votos
            FROM usuarios WHERE campeon_favorito IS NOT NULL
            GROUP BY campeon_favorito ORDER BY votos DESC LIMIT 12
        """).fetchall()

        jugador_stats = conn.execute("""
            SELECT jugador_favorito AS jugador, COUNT(*) AS votos
            FROM usuarios WHERE jugador_favorito IS NOT NULL AND jugador_favorito != ''
            GROUP BY jugador_favorito ORDER BY votos DESC LIMIT 10
        """).fetchall()

        marcadores_stats = conn.execute("""
            SELECT goles_local, goles_visita, COUNT(*) AS total
            FROM predicciones
            GROUP BY goles_local, goles_visita ORDER BY total DESC LIMIT 10
        """).fetchall()

        goleador_stats = conn.execute("""
            SELECT goleador_mundial AS jugador, COUNT(*) AS votos
            FROM usuarios WHERE goleador_mundial IS NOT NULL AND goleador_mundial != ''
            GROUP BY goleador_mundial ORDER BY votos DESC LIMIT 8
        """).fetchall()

        mas_goleador_stats = conn.execute("""
            SELECT equipo_mas_goleador AS equipo, COUNT(*) AS votos
            FROM usuarios WHERE equipo_mas_goleador IS NOT NULL
            GROUP BY equipo_mas_goleador ORDER BY votos DESC LIMIT 8
        """).fetchall()

        sorpresa_stats = conn.execute("""
            SELECT equipo_sorpresa AS equipo, COUNT(*) AS votos
            FROM usuarios WHERE equipo_sorpresa IS NOT NULL
            GROUP BY equipo_sorpresa ORDER BY votos DESC LIMIT 8
        """).fetchall()

        decepcion_stats = conn.execute("""
            SELECT equipo_decepcion AS equipo, COUNT(*) AS votos
            FROM usuarios WHERE equipo_decepcion IS NOT NULL
            GROUP BY equipo_decepcion ORDER BY votos DESC LIMIT 8
        """).fetchall()

    liga_id = request.args.get("liga", type=int)
    if liga_id is None:
        ligas_usuario = current_user.ligas()
        if ligas_usuario:
            ids_usuario = [l["id"] for l in ligas_usuario]
            tct = next((l for l in ligas_usuario if "todos" in l["nombre"].lower()), None)
            if tct:
                liga_id = tct["id"]
            elif len(ids_usuario) == 1:
                liga_id = ids_usuario[0]

    tabla       = get_ranking(liga_id=liga_id)
    equipos_iso = _equipos_iso()

    return render_template(
        "ranking/index.html",
        tabla=tabla,
        ligas=[dict(l) for l in ligas],
        liga_id=liga_id,
        fases=FASES,
        campeon_stats=[dict(r) for r in campeon_stats],
        jugador_stats=[dict(r) for r in jugador_stats],
        marcadores_stats=[dict(r) for r in marcadores_stats],
        goleador_stats=[dict(r) for r in goleador_stats],
        mas_goleador_stats=[dict(r) for r in mas_goleador_stats],
        sorpresa_stats=[dict(r) for r in sorpresa_stats],
        decepcion_stats=[dict(r) for r in decepcion_stats],
        equipos_iso=equipos_iso,
    )


@ranking_bp.route("/debug")
@login_required
def debug():
    """Diagnóstico del estado de la DB. Solo admins."""
    if not getattr(current_user, 'es_admin', False):
        abort(403)

    out = []

    out.append("=== PARTIDOS EN DB CON RESULTADO ===")
    with get_db() as conn:
        partidos_res = conn.execute("""
            SELECT id, equipo_local, equipo_visita, fecha,
                   goles_local, goles_visita, fase
            FROM partidos WHERE goles_local IS NOT NULL ORDER BY fecha
        """).fetchall()
        out.append(f"Total: {len(partidos_res)}")
        for p in partidos_res:
            out.append(f"  id={p['id']} {p['equipo_local']} {p['goles_local']}-{p['goles_visita']} {p['equipo_visita']}  fecha={p['fecha']}  fase={p['fase']}")

        out.append("\n=== PREDICCIONES CON PUNTOS ===")
        preds = conn.execute("""
            SELECT u.nickname, pa.equipo_local, pa.equipo_visita,
                   pr.goles_local, pr.goles_visita, pr.puntos_obtenidos
            FROM predicciones pr
            JOIN usuarios u ON u.id = pr.usuario_id
            JOIN partidos pa ON pa.id = pr.partido_id
            WHERE pa.goles_local IS NOT NULL
            ORDER BY u.nickname
        """).fetchall()
        if not preds:
            out.append("  (ninguna)")
        for pr in preds:
            out.append(f"  {pr['nickname']}: {pr['equipo_local']} vs {pr['equipo_visita']}  pred={pr['goles_local']}-{pr['goles_visita']}  pts={pr['puntos_obtenidos']}")

        out.append("\n=== PUNTAJES_FASE ===")
        pf = conn.execute("""
            SELECT u.nickname, pf.fase, pf.puntos
            FROM puntajes_fase pf JOIN usuarios u ON u.id = pf.usuario_id
            ORDER BY pf.puntos DESC
        """).fetchall()
        if not pf:
            out.append("  (vacío)")
        for row in pf:
            out.append(f"  {row['nickname']} / {row['fase']}: {row['puntos']} pts")

    return Response('\n'.join(out), mimetype='text/plain')
