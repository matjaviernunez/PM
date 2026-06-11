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
