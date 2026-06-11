"""
ranking/routes.py — Tabla de posiciones general y por liga.
"""

import json, os, time, threading
from flask import Blueprint, render_template, request, jsonify, Response, abort
from flask_login import login_required, current_user

from game.scoring import get_ranking
from db import get_db
from config import FASES, BASE_DIR

ranking_bp = Blueprint("ranking", __name__,
                       template_folder="../templates/ranking")

# Rate-limit: no llamar ESPN más de una vez cada 45 s
_last_sync_ts  = 0.0
_sync_lock     = threading.Lock()
_SYNC_INTERVAL = 45


def _equipos_iso():
    path = os.path.join(BASE_DIR, "data", "equipos.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m = {}
    for equipos in data["grupos"].values():
        for e in equipos:
            m[e["codigo"]] = e["iso"]
    return m


def _sync_if_due():
    """Corre sync_scores() si pasaron más de _SYNC_INTERVAL segundos."""
    global _last_sync_ts
    now = time.monotonic()
    if now - _last_sync_ts < _SYNC_INTERVAL:
        return
    if not _sync_lock.acquire(blocking=False):
        return
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


@ranking_bp.route("/")
@login_required
def index():
    _sync_if_due()

    with get_db() as conn:
        ligas = conn.execute(
            "SELECT id, nombre FROM ligas ORDER BY nombre"
        ).fetchall()

        campeon_stats = conn.execute("""
            SELECT campeon_favorito AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE campeon_favorito IS NOT NULL
            GROUP BY campeon_favorito
            ORDER BY votos DESC
            LIMIT 12
        """).fetchall()

        jugador_stats = conn.execute("""
            SELECT jugador_favorito AS jugador, COUNT(*) AS votos
            FROM usuarios
            WHERE jugador_favorito IS NOT NULL AND jugador_favorito != ''
            GROUP BY jugador_favorito
            ORDER BY votos DESC
            LIMIT 10
        """).fetchall()

        marcadores_stats = conn.execute("""
            SELECT goles_local, goles_visita, COUNT(*) AS total
            FROM predicciones
            GROUP BY goles_local, goles_visita
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

        goleador_stats = conn.execute("""
            SELECT goleador_mundial AS jugador, COUNT(*) AS votos
            FROM usuarios
            WHERE goleador_mundial IS NOT NULL AND goleador_mundial != ''
            GROUP BY goleador_mundial
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        mas_goleador_stats = conn.execute("""
            SELECT equipo_mas_goleador AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_mas_goleador IS NOT NULL
            GROUP BY equipo_mas_goleador
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        sorpresa_stats = conn.execute("""
            SELECT equipo_sorpresa AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_sorpresa IS NOT NULL
            GROUP BY equipo_sorpresa
            ORDER BY votos DESC
            LIMIT 8
        """).fetchall()

        decepcion_stats = conn.execute("""
            SELECT equipo_decepcion AS equipo, COUNT(*) AS votos
            FROM usuarios
            WHERE equipo_decepcion IS NOT NULL
            GROUP BY equipo_decepcion
            ORDER BY votos DESC
            LIMIT 8
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


@ranking_bp.route("/debug")
@login_required
def debug():
    """Diagnóstico completo ESPN → DB → puntajes. Solo admins."""
    if not getattr(current_user, 'es_admin', False):
        abort(403)

    import urllib.request as _ureq, json as _json
    from game.espn_sync import ESPN_SCOREBOARD, _espn_date_to_ect, sync_scores

    out = []

    # 1. ESPN raw
    out.append("=== 1. ESPN SCOREBOARD ===")
    try:
        req = _ureq.Request(ESPN_SCOREBOARD,
              headers={'User-Agent': 'Mozilla/5.0 PollaMundial/1.0'})
        with _ureq.urlopen(req, timeout=10) as r:
            espn_data = _json.loads(r.read())
        events = espn_data.get('events', [])
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
            raw_date = e.get('date', '') or comp.get('date', '')
            fecha_ect = _espn_date_to_ect(raw_date)
            out.append(f"  [{state}] {ha} {hs}-{as_} {aa}  fecha_ect={fecha_ect}  raw={raw_date}")
    except Exception as ex:
        out.append(f"  ERROR ESPN: {ex}")

    # 2. Partidos en DB con resultado
    out.append("\n=== 2. PARTIDOS EN DB CON RESULTADO ===")
    with get_db() as conn:
        partidos_res = conn.execute("""
            SELECT id, equipo_local, equipo_visita, fecha,
                   goles_local, goles_visita, fase
            FROM partidos
            WHERE goles_local IS NOT NULL
            ORDER BY fecha
        """).fetchall()
        if not partidos_res:
            out.append("  (ninguno — DB no tiene resultados aún)")
        for p in partidos_res:
            out.append(f"  id={p['id']} {p['equipo_local']} {p['goles_local']}-{p['goles_visita']} {p['equipo_visita']}  fecha={p['fecha']}  fase={p['fase']}")

        # 3. Predicciones con puntos_obtenidos
        out.append("\n=== 3. PREDICCIONES (puntos_obtenidos) ===")
        preds_all = conn.execute("""
            SELECT u.nickname, p.equipo_local, p.equipo_visita,
                   pr.goles_local, pr.goles_visita, pr.puntos_obtenidos
            FROM predicciones pr
            JOIN usuarios u  ON u.id  = pr.usuario_id
            JOIN partidos p  ON p.id  = pr.partido_id
            WHERE p.goles_local IS NOT NULL
            ORDER BY u.nickname
        """).fetchall()
        if not preds_all:
            out.append("  (sin predicciones para partidos con resultado)")
        for pr in preds_all:
            out.append(f"  {pr['nickname']}: {pr['equipo_local']} vs {pr['equipo_visita']}  pred={pr['goles_local']}-{pr['goles_visita']}  pts={pr['puntos_obtenidos']}")

        # 4. puntajes_fase
        out.append("\n=== 4. PUNTAJES_FASE ===")
        pf = conn.execute("""
            SELECT u.nickname, pf.fase, pf.puntos
            FROM puntajes_fase pf
            JOIN usuarios u ON u.id = pf.usuario_id
            ORDER BY pf.puntos DESC
        """).fetchall()
        if not pf:
            out.append("  (vacío)")
        for row in pf:
            out.append(f"  {row['nickname']} / {row['fase']}: {row['puntos']} pts")

    # 5. Forzar sync (fuera del bloque get_db para evitar conexiones anidadas)
    out.append("\n=== 5. FORZAR SYNC AHORA ===")
    try:
        result = sync_scores()
        out.append(f"  Resultado: {result}")
    except Exception as ex:
        out.append(f"  ERROR: {ex}")

    # 6. puntajes_fase DESPUÉS del sync
    out.append("\n=== 6. PUNTAJES_FASE DESPUÉS DEL SYNC ===")
    with get_db() as conn2:
        pf2 = conn2.execute("""
            SELECT u.nickname, pf.fase, pf.puntos
            FROM puntajes_fase pf
            JOIN usuarios u ON u.id = pf.usuario_id
            ORDER BY pf.puntos DESC
        """).fetchall()
        if not pf2:
            out.append("  (sigue vacío)")
        for row in pf2:
            out.append(f"  {row['nickname']} / {row['fase']}: {row['puntos']} pts")

    return Response('\n'.join(out), mimetype='text/plain')
