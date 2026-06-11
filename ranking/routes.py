"""
ranking/routes.py — Tabla de posiciones general y por liga.
"""

import json, os, time, threading
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from game.scoring import get_ranking
from db import get_db
from config import FASES, BASE_DIR

# Rate-limit para no llamar ESPN en cada clic consecutivo
_last_sync_ts   = 0.0
_sync_lock      = threading.Lock()
_SYNC_INTERVAL  = 45  # segundos mínimos entre syncs


@ranking_bp.route("/debug")
@login_required
def debug():
    """Diagnóstico: ESPN raw → DB → puntajes. Solo para admins."""
    from flask_login import current_user
    if not getattr(current_user, 'es_admin', False):
        from flask import abort; abort(403)

    import urllib.request, json as _json
    from datetime import datetime, timedelta, timezone
    from game.espn_sync import ESPN_SCOREBOARD, _espn_date_to_ect
    from game.scoring import recalcular_partido

    out = []

    # 1. ESPN raw
    out.append("=== 1. ESPN SCOREBOARD ===")
    try:
        req = urllib.request.Request(ESPN_SCOREBOARD,
              headers={'User-Agent': 'Mozilla/5.0 PollaMundial/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read())
        events = data.get('events', [])
        out.append(f"Total eventos: {len(events)}")
        for e in events:
            state = e.get('status', {}).get('type', {}).get('state', '?')
            comp  = e.get('competitions', [{}])[0]
            teams = comp.get('competitors', [])
            home  = next((c for c in teams if c.get('homeAway') == 'home'), {})
            away  = next((c for c in teams if c.get('homeAway') == 'away'), {})
            ha    = home.get('team', {}).get('abbreviation', '?')
            aa    = away.get('team', {}).get('abbreviation', '?')
            hs    = home.get('score', '?')
            as_   = away.get('score', '?')
            fecha = _espn_date_to_ect(e.get('date', '') or comp.get('date', ''))
            out.append(f"  [{state}] {ha} {hs}-{as_} {aa}  fecha_ect={fecha}  espn_date={e.get('date','?')}")
    except Exception as ex:
        out.append(f"ERROR ESPN: {ex}")

    # 2. Partidos en DB con resultado
    out.append("\n=== 2. PARTIDOS EN DB CON RESULTADO ===")
    with get_db() as conn:
        partidos_res = conn.execute("""
            SELECT id, equipo_local, equipo_visita, fecha, hora,
                   goles_local, goles_visita, penales_local, penales_visita, fase
            FROM partidos
            WHERE goles_local IS NOT NULL
            ORDER BY fecha, hora
        """).fetchall()
        if not partidos_res:
            out.append("  (ninguno)")
        for p in partidos_res:
            out.append(f"  id={p['id']} {p['equipo_local']} {p['goles_local']}-{p['goles_visita']} {p['equipo_visita']}  fecha={p['fecha']}  fase={p['fase']}")

        # 3. Predicciones para esos partidos
        out.append("\n=== 3. PREDICCIONES DE PARTIDOS CON RESULTADO ===")
        for p in partidos_res:
            preds = conn.execute("""
                SELECT pr.id, u.nickname, pr.goles_local, pr.goles_visita,
                       pr.penales_local, pr.penales_visita, pr.puntos_obtenidos
                FROM predicciones pr
                JOIN usuarios u ON u.id = pr.usuario_id
                WHERE pr.partido_id = ?
            """, (p['id'],)).fetchall()
            out.append(f"  Partido {p['id']} ({p['equipo_local']} vs {p['equipo_visita']}):")
            if not preds:
                out.append("    (sin predicciones)")
            for pr in preds:
                out.append(f"    {pr['nickname']}: pred={pr['goles_local']}-{pr['goles_visita']}  pts_obtenidos={pr['puntos_obtenidos']}")

        # 4. puntajes_fase
        out.append("\n=== 4. PUNTAJES_FASE ===")
        pf = conn.execute("""
            SELECT u.nickname, pf.fase, pf.puntos
            FROM puntajes_fase pf
            JOIN usuarios u ON u.id = pf.usuario_id
            ORDER BY u.nickname, pf.fase
        """).fetchall()
        if not pf:
            out.append("  (vacío)")
        for row in pf:
            out.append(f"  {row['nickname']} / {row['fase']}: {row['puntos']} pts")

        # 5. Forzar sync y mostrar resultado
        out.append("\n=== 5. FORZAR SYNC AHORA ===")
        try:
            from game.espn_sync import sync_scores
            result = sync_scores()
            out.append(f"  Resultado: {result}")
        except Exception as ex:
            out.append(f"  ERROR: {ex}")

        # 6. puntajes_fase DESPUÉS del sync
        out.append("\n=== 6. PUNTAJES_FASE DESPUÉS DEL SYNC ===")
        pf2 = conn.execute("""
            SELECT u.nickname, pf.fase, pf.puntos
            FROM puntajes_fase pf
            JOIN usuarios u ON u.id = pf.usuario_id
            ORDER BY u.nickname, pf.fase
        """).fetchall()
        if not pf2:
            out.append("  (sigue vacío)")
        for row in pf2:
            out.append(f"  {row['nickname']} / {row['fase']}: {row['puntos']} pts")

    from flask import Response
    return Response('\n'.join(out), mimetype='text/plain')


def _sync_if_due():
    """Corre sync_scores() si pasaron más de _SYNC_INTERVAL segundos."""
    global _last_sync_ts
    now = time.monotonic()
    if now - _last_sync_ts < _SYNC_INTERVAL:
        return
    if not _sync_lock.acquire(blocking=False):
        return  # otra request ya está sincronizando
    try:
        _last_sync_ts = now
        from game.espn_sync import sync_scores
        result = sync_scores()
        if result['actualizados']:
            import logging
            logging.getLogger(__name__).info('Ranking sync: %s', result)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning('Ranking sync error: %s', exc)
    finally:
        _sync_lock.release()

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
    # Sincronizar con ESPN si corresponde (rate-limited a cada 45 s)
    _sync_if_due()

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

        # Distribución de jugador favorito
        jugador_stats = conn.execute("""
            SELECT jugador_favorito AS jugador, COUNT(*) AS votos
            FROM usuarios
            WHERE jugador_favorito IS NOT NULL AND jugador_favorito != ''
            GROUP BY jugador_favorito
            ORDER BY votos DESC
            LIMIT 10
        """).fetchall()

        # Marcadores más predichos
        marcadores_stats = conn.execute("""
            SELECT goles_local, goles_visita, COUNT(*) AS total
            FROM predicciones
            GROUP BY goles_local, goles_visita
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

        # Goleador del mundial
        goleador_stats = conn.execute("""
            SELECT goleador_mundial AS jugador, COUNT(*) AS votos
            FROM usuarios
            WHERE goleador_mundial IS NOT NULL AND goleador_mundial != ''
            GROUP BY goleador_mundial
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        # Equipo más goleador
        mas_goleador_stats = conn.execute("""
            SELECT equipo_mas_goleador AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_mas_goleador IS NOT NULL
            GROUP BY equipo_mas_goleador
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        # Equipo sorpresa
        sorpresa_stats = conn.execute("""
            SELECT equipo_sorpresa AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_sorpresa IS NOT NULL
            GROUP BY equipo_sorpresa
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        # Equipo decepción
        decepcion_stats = conn.execute("""
            SELECT equipo_decepcion AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_decepcion IS NOT NULL
            GROUP BY equipo_decepcion
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

    liga_id = request.args.get("liga", type=int)

    # Si no se especificó liga, inferir la default del usuario
    if liga_id is None:
        ligas_usuario = current_user.ligas()
        if ligas_usuario:
            ids_usuario = [l["id"] for l in ligas_usuario]
            # Buscar "Todos contra todos" primero
            tct = next((l for l in ligas_usuario if "todos" in l["nombre"].lower()), None)
            if tct:
                liga_id = tct["id"]
            elif len(ids_usuario) == 1:
                liga_id = ids_usuario[0]
            # Si tiene varias ligas (sin Todos contra todos) → sin default

    tabla      = get_ranking(liga_id=liga_id)
    equipos_iso = _equipos_iso()

    # Ultima sincronizacion con ESPN
    from game import espn_sync as _sync
    last_sync = _sync.last_sync_time.strftime('%H:%M:%S') if _sync.last_sync_time else None

    return render_template(
        "ranking/index.html",
        last_sync=last_sync,
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
