"""
game/models.py -- Queries de partidos y predicciones.
"""

from datetime import datetime, date, timedelta
from db import get_db


# -- Partidos ---------------------------------------------------------------

def get_partidos_por_grupo(grupo: str) -> list[dict]:
    """Retorna los 6 partidos de un grupo ordenados por fecha/hora."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM partidos
            WHERE fase = 'grupos' AND grupo = ?
            ORDER BY fecha, hora
        """, (grupo,)).fetchall()
    return [dict(r) for r in rows]


def get_todos_partidos_grupos() -> list[dict]:
    """Retorna los 72 partidos de grupos ordenados por fecha/hora."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM partidos
            WHERE fase = 'grupos'
            ORDER BY fecha, hora
        """).fetchall()
    return [dict(r) for r in rows]


def get_partidos_eliminatorias() -> list[dict]:
    """
    Retorna todos los partidos de fases knockout (no grupos)
    ordenados por fase, fecha, hora.
    Solo incluye fases que ya tienen partidos en la DB.
    """
    fases_orden = ['16avos', 'octavos', 'cuartos', 'semis', '3er_puesto', 'final']
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM partidos
            WHERE fase != 'grupos'
            ORDER BY fecha, hora
        """).fetchall()
    partidos = [dict(r) for r in rows]

    # Ordenar por fase segun jerarquia definida
    def fase_key(p):
        try:
            return fases_orden.index(p['fase'])
        except ValueError:
            return 99

    partidos.sort(key=lambda p: (fase_key(p), p['fecha'] or '', p['hora'] or ''))
    return partidos


def get_fases_eliminatorias_disponibles() -> list[str]:
    """Retorna lista de fases knockout que ya tienen partidos en DB."""
    fases_orden = ['16avos', 'octavos', 'cuartos', 'semis', '3er_puesto', 'final']
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT fase FROM partidos WHERE fase != 'grupos'
        """).fetchall()
    fases = [r['fase'] for r in rows]
    return [f for f in fases_orden if f in fases]


def guardar_predicciones_lote(usuario_id: int, predicciones: list[dict]) -> dict:
    """
    Guarda multiples predicciones de una vez.
    predicciones: [{partido_id, goles_local, goles_visita}, ...]
    Retorna {guardados: N, cerrados: N}
    """
    guardados = 0
    cerrados  = 0
    for p in predicciones:
        ok = guardar_prediccion(
            usuario_id=usuario_id,
            partido_id=p['partido_id'],
            goles_local=p['goles_local'],
            goles_visita=p['goles_visita'],
        )
        if ok:
            guardados += 1
        else:
            cerrados += 1
    return {'guardados': guardados, 'cerrados': cerrados}


def cerrar_partidos_vencidos():
    """Marca como cerrados los partidos cuya fecha/hora ya paso (hora Ecuador UTC-5).
    También actualiza estado a 'in' para los que acaban de empezar (sin resultado aún).
    """
    # El servidor corre en UTC; los horarios en la DB estan en hora Ecuador (UTC-5)
    ahora_ecuador = datetime.utcnow() - timedelta(hours=5)
    with get_db() as conn:
        conn.execute("""
            UPDATE partidos
            SET abierto = FALSE,
                estado  = CASE
                    WHEN estado = 'pre' THEN 'in'
                    ELSE estado
                END
            WHERE abierto = TRUE
              AND datetime(fecha || ' ' || hora) <= ?
        """, (ahora_ecuador.strftime('%Y-%m-%d %H:%M'),))
        conn.commit()


# -- Predicciones -----------------------------------------------------------

def get_predicciones_usuario(usuario_id: int, partido_ids: list[int]) -> dict:
    """
    Retorna un dict {partido_id: prediccion_dict} para los partidos dados.
    """
    if not partido_ids:
        return {}
    placeholders = ','.join('?' * len(partido_ids))
    with get_db() as conn:
        rows = conn.execute(f"""
            SELECT * FROM predicciones
            WHERE usuario_id = ? AND partido_id IN ({placeholders})
        """, (usuario_id, *partido_ids)).fetchall()
    return {r['partido_id']: dict(r) for r in rows}


def guardar_prediccion(usuario_id: int, partido_id: int,
                       goles_local: int, goles_visita: int,
                       penales_local: int = None,
                       penales_visita: int = None) -> bool:
    """
    Inserta o actualiza una prediccion.
    Para eliminatorias: si goles_local == goles_visita, se esperan penales_local/visita.
    Retorna False si el partido ya cerro.
    """
    with get_db() as conn:
        partido = conn.execute(
            'SELECT abierto FROM partidos WHERE id = ?', (partido_id,)
        ).fetchone()

        if not partido or not partido['abierto']:
            return False

        conn.execute("""
            INSERT INTO predicciones
                (usuario_id, partido_id, goles_local, goles_visita,
                 penales_local, penales_visita)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(usuario_id, partido_id) DO UPDATE SET
                goles_local    = excluded.goles_local,
                goles_visita   = excluded.goles_visita,
                penales_local  = excluded.penales_local,
                penales_visita = excluded.penales_visita
        """, (usuario_id, partido_id, goles_local, goles_visita,
              penales_local, penales_visita))
        conn.commit()
    return True


# -- Clasificacion unica de estado de un partido --------------------------
# Fuente unica de verdad para UI y orden. Basada en el TIEMPO (kickoff en
# hora Ecuador), no en la columna 'estado' (que puede quedar desincronizada).
#   - 'proximo' : aun no empieza
#   - 'en_vivo' : empezo y esta dentro de la ventana de juego
#   - 'final'   : termino (paso la ventana) o estado='post' explicito
DUR_PARTIDO_MIN = 150  # ventana de "en vivo" tras el kickoff (minutos)

ORDEN_ESTADO = {'en_vivo': 0, 'proximo': 1, 'final': 2}


def estado_partido(p, ahora_ect=None) -> str:
    """Retorna 'proximo' | 'en_vivo' | 'final' para un partido (dict o Row)."""
    if ahora_ect is None:
        ahora_ect = datetime.utcnow() - timedelta(hours=5)  # hora Ecuador UTC-5

    estado = (p['estado'] if 'estado' in p.keys() else None) if hasattr(p, 'keys') else None
    if estado is None:
        try:
            estado = p.get('estado')
        except AttributeError:
            estado = None
    if estado == 'post':
        return 'final'

    fecha = p['fecha'] if hasattr(p, 'keys') else p.get('fecha')
    hora  = p['hora']  if hasattr(p, 'keys') else p.get('hora')
    goles = p['goles_local'] if hasattr(p, 'keys') else p.get('goles_local')

    try:
        kickoff = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        # Sin hora fiable: usar el resultado como proxy
        return 'final' if goles is not None else 'proximo'

    if ahora_ect < kickoff:
        return 'proximo'
    if ahora_ect < kickoff + timedelta(minutes=DUR_PARTIDO_MIN):
        return 'en_vivo'
    return 'final'
