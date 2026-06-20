"""
game/scoring.py -- Motor de puntuacion de la polla.

GRUPOS (tiempo reglamentario):
  - Acertar resultado (W/D/L)    -> 1 pt
  - + Diferencia de goles exacta -> 1 pt (requiere resultado correcto)
  - + Marcador exacto            -> 2 pts (requiere diferencia correcta)
  Maximo: 4 pts.

ELIMINATORIAS:
  El punto de "acertar resultado" se REEMPLAZA por "acertar quien avanza":
  - Acertar quien avanza         -> 1 pt
      (el equipo que predijiste que pasa == el que paso; tu avanzador es el
       que predijiste ganando en 90'/prorroga, o el ganador de penales que
       pusiste si predijiste empate)
  - + Diferencia exacta en TR    -> 1 pt (independiente de quien avanza)
  - + Marcador exacto en TR      -> 2 pts (requiere diferencia correcta)
  Maximo: 4 pts. El marcador de la tanda no se puntua, solo quien gana.

Multiplicadores por fase:
  grupos / 16avos            -> x1
  octavos / cuartos          -> x2
  semis / 3er_puesto / final -> x3
"""

from db import get_db
from config import MULTIPLICADORES


# -- Calculo de puntos para un partido ------------------------------------

def calcular_puntos(
    pred_local: int, pred_visita: int,
    real_local: int, real_visita: int,
    fase: str,
    pred_pen_local: int = None,  pred_pen_visita: int = None,
    real_pen_local: int = None,  real_pen_visita: int = None,
    real_pen_ganador: str = None,
) -> int:
    multiplicador = MULTIPLICADORES.get(fase, 1)
    puntos = 0

    pred_diff = pred_local - pred_visita
    real_diff = real_local - real_visita
    pred_res = (pred_local > pred_visita) - (pred_local < pred_visita)
    real_res = (real_local > real_visita) - (real_local < real_visita)

    if fase == "grupos":
        # Grupos: resultado (W/D/L) -> diferencia -> marcador exacto
        if pred_res == real_res:
            puntos += 1
            if pred_diff == real_diff:
                puntos += 1
                if pred_local == real_local and pred_visita == real_visita:
                    puntos += 2
        return puntos * multiplicador

    # -- Eliminatorias ----------------------------------------------------
    # El punto de "acertar resultado" se reemplaza por "acertar quien avanza".
    # Equipo que el usuario predijo que avanza:
    if pred_res != 0:
        pred_avanza = "local" if pred_res > 0 else "visita"
    elif pred_pen_local is not None and pred_pen_visita is not None:
        pred_avanza = "local" if pred_pen_local > pred_pen_visita else "visita"
    else:
        pred_avanza = None  # predijo empate sin indicar ganador de penales

    # Equipo que realmente avanza:
    if real_res != 0:
        real_avanza = "local" if real_res > 0 else "visita"
    elif real_pen_local is not None and real_pen_visita is not None:
        real_avanza = "local" if real_pen_local > real_pen_visita else "visita"
    elif real_pen_ganador in ("local", "visita"):
        real_avanza = real_pen_ganador
    else:
        real_avanza = None  # empate sin penales (no deberia ocurrir en KO)

    # +1 por acertar quien avanza (reemplaza "acertar resultado")
    if real_avanza is not None and pred_avanza == real_avanza:
        puntos += 1

    # +1 diferencia exacta y +2 marcador exacto del tiempo reglamentario
    if pred_diff == real_diff:
        puntos += 1
        if pred_local == real_local and pred_visita == real_visita:
            puntos += 2

    return puntos * multiplicador


# -- Recalcular puntos de un partido ya jugado ----------------------------

def recalcular_partido(partido_id: int) -> int:
    """
    Recalcula los puntos de todas las predicciones de un partido.
    Idempotente: resta los puntos anteriores antes de agregar los nuevos,
    por lo que puede llamarse multiples veces sin duplicar puntajes.
    Retorna el numero de predicciones procesadas.
    """
    with get_db() as conn:
        partido = conn.execute(
            'SELECT * FROM partidos WHERE id = ?', (partido_id,)
        ).fetchone()

        if not partido:
            return 0
        if partido['goles_local'] is None or partido['goles_visita'] is None:
            return 0

        predicciones = conn.execute(
            'SELECT * FROM predicciones WHERE partido_id = ?', (partido_id,)
        ).fetchall()

        procesadas = 0
        for pred in predicciones:
            # Restar puntos anteriores de puntajes_fase (si existian)
            old_pts = pred['puntos_obtenidos'] or 0
            if old_pts:
                conn.execute("""
                    UPDATE puntajes_fase SET puntos = MAX(0, puntos - ?)
                    WHERE usuario_id = ? AND fase = ?
                """, (old_pts, pred['usuario_id'], partido['fase']))

            puntos = calcular_puntos(
                pred_local=pred['goles_local'],
                pred_visita=pred['goles_visita'],
                real_local=partido['goles_local'],
                real_visita=partido['goles_visita'],
                fase=partido['fase'],
                pred_pen_local=pred['penales_local'],
                pred_pen_visita=pred['penales_visita'],
                real_pen_local=partido['penales_local'],
                real_pen_visita=partido['penales_visita'],
            )

            conn.execute(
                'UPDATE predicciones SET puntos_obtenidos = ? WHERE id = ?',
                (puntos, pred['id'])
            )

            conn.execute("""
                INSERT INTO puntajes_fase (usuario_id, fase, puntos)
                VALUES (?, ?, ?)
                ON CONFLICT(usuario_id, fase) DO UPDATE SET
                    puntos = puntos + excluded.puntos
            """, (pred['usuario_id'], partido['fase'], puntos))

            procesadas += 1

        conn.commit()
    return procesadas


# -- Ranking general -------------------------------------------------------

def get_ranking(liga_id: int = None) -> list[dict]:
    """
    Retorna lista de {usuario_id, nickname, codigo, total, por_fase}
    ordenada por puntos desc.
    """
    with get_db() as conn:
        if liga_id:
            usuarios = conn.execute("""
                SELECT u.id, u.nickname, u.codigo, u.equipo_favorito, u.campeon_favorito
                FROM usuarios u
                JOIN usuario_liga ul ON ul.usuario_id = u.id
                WHERE ul.liga_id = ?
            """, (liga_id,)).fetchall()
        else:
            usuarios = conn.execute(
                'SELECT id, nickname, codigo, equipo_favorito, campeon_favorito FROM usuarios'
            ).fetchall()

        ranking = []
        for u in usuarios:
            fases = conn.execute("""
                SELECT fase, puntos FROM puntajes_fase WHERE usuario_id = ?
            """, (u['id'],)).fetchall()

            por_fase = {f['fase']: f['puntos'] for f in fases}
            total = sum(por_fase.values())

            exactos = conn.execute("""
                SELECT COUNT(*) as n FROM predicciones
                WHERE usuario_id = ? AND puntos_obtenidos IS NOT NULL
                  AND goles_local = (
                      SELECT goles_local FROM partidos WHERE id = partido_id
                  )
                  AND goles_visita = (
                      SELECT goles_visita FROM partidos WHERE id = partido_id
                  )
            """, (u['id'],)).fetchone()['n']

            ranking.append({
                'usuario_id':       u['id'],
                'nickname':         u['nickname'],
                'codigo':           u['codigo'],
                'equipo_favorito':  u['equipo_favorito'],
                'campeon_favorito': u['campeon_favorito'],
                'total':            total,
                'por_fase':         por_fase,
                'exactos':          exactos,
            })

        ranking.sort(key=lambda x: (-x['total'], -x['exactos'], x['nickname']))

    return ranking
