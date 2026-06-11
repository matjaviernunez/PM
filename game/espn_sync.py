"""
game/espn_sync.py — Sincronización automática de resultados desde ESPN API.

Corre cada 60 s via APScheduler (ver app.py).
Identifica partidos por equipo_local + equipo_visita (códigos idénticos a ESPN).
Verifica la fecha como seguridad adicional.
Solo escribe en DB cuando el marcador cambia — idempotente.
"""

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

from db import get_db
from game.scoring import recalcular_partido

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = (
    'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard'
)

# Cache en memoria: partido_id -> (goles_local, goles_visita, state)
# Evita recalcular si el marcador no cambió entre ticks.
_last_known: dict[int, tuple] = {}

# Última vez que se ejecutó con éxito
last_sync_time: datetime | None = None


def _fetch_scoreboard() -> list[dict]:
    """Descarga el scoreboard de ESPN y retorna la lista de eventos."""
    try:
        req = urllib.request.Request(
            ESPN_SCOREBOARD,
            headers={'User-Agent': 'Mozilla/5.0 PollaMundial/1.0'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get('events', [])
    except Exception as exc:
        logger.warning('ESPN sync — fetch error: %s', exc)
        return []


def _espn_date_to_ect(date_str: str) -> str | None:
    """
    Convierte la fecha UTC del evento ESPN (ISO 8601) a fecha Ecuador (UTC-5).
    Retorna 'YYYY-MM-DD' o None si no puede parsear.
    """
    try:
        # ESPN envía algo como '2026-06-11T19:00Z'
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        dt_ect = dt.astimezone(timezone(timedelta(hours=-5)))
        return dt_ect.strftime('%Y-%m-%d')
    except Exception:
        return None


def sync_scores() -> dict:
    """
    Descarga el scoreboard de ESPN, cruza con nuestra DB por equipos y fecha,
    actualiza marcadores y recalcula puntos solo cuando hay cambios.

    Retorna {'actualizados': N, 'recalculados': N, 'errores': N}.
    """
    global last_sync_time

    events = _fetch_scoreboard()
    # Solo partidos en curso o terminados
    events = [
        e for e in events
        if e.get('status', {}).get('type', {}).get('state') in ('in', 'post')
    ]

    if not events:
        last_sync_time = datetime.now()
        return {'actualizados': 0, 'recalculados': 0, 'errores': 0}

    actualizados = 0
    recalculados = 0
    errores = 0

    with get_db() as conn:
        for event in events:
            try:
                comp        = event.get('competitions', [{}])[0]
                competitors = comp.get('competitors', [])
                home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                if not home or not away:
                    continue

                home_abbr = home.get('team', {}).get('abbreviation', '')
                away_abbr = away.get('team', {}).get('abbreviation', '')
                if not home_abbr or not away_abbr:
                    continue

                try:
                    gl = int(home.get('score') or 0)
                    gv = int(away.get('score') or 0)
                except (ValueError, TypeError):
                    continue

                state = event.get('status', {}).get('type', {}).get('state', '')

                # Fecha del evento en hora Ecuador (verificación extra)
                espn_date = _espn_date_to_ect(
                    event.get('date', '')
                    or comp.get('date', '')
                )

                # Buscar partido en DB por equipos + fecha (si tenemos fecha)
                if espn_date:
                    partido = conn.execute("""
                        SELECT id, goles_local, goles_visita, penales_local,
                               penales_visita, fase
                        FROM partidos
                        WHERE equipo_local = ? AND equipo_visita = ?
                          AND fecha = ?
                    """, (home_abbr, away_abbr, espn_date)).fetchone()
                else:
                    partido = conn.execute("""
                        SELECT id, goles_local, goles_visita, penales_local,
                               penales_visita, fase
                        FROM partidos
                        WHERE equipo_local = ? AND equipo_visita = ?
                    """, (home_abbr, away_abbr)).fetchone()

                if not partido:
                    logger.debug(
                        'ESPN sync — partido no encontrado: %s vs %s (%s)',
                        home_abbr, away_abbr, espn_date
                    )
                    continue

                pid   = partido['id']
                curr  = (gl, gv, state)
                prev  = _last_known.get(pid)

                if prev == curr:
                    continue  # Sin cambios — skip

                _last_known[pid] = curr

                # Actualizar marcador en DB
                conn.execute("""
                    UPDATE partidos SET goles_local = ?, goles_visita = ?
                    WHERE id = ?
                """, (gl, gv, pid))
                conn.commit()
                actualizados += 1

                # Recalcular puntos (idempotente gracias al fix en scoring.py)
                recalcular_partido(pid)
                recalculados += 1

                logger.info(
                    'ESPN sync — %s %d-%d %s [%s]',
                    f'{home_abbr} vs {away_abbr}', gl, gv, state, espn_date or '?'
                )

            except Exception as exc:
                logger.error('ESPN sync — error procesando evento: %s', exc)
                errores += 1

    last_sync_time = datetime.now()
    return {'actualizados': actualizados, 'recalculados': recalculados, 'errores': errores}
