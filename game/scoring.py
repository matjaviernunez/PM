"""
game/scoring.py -- Motor de puntuacion de la polla.

Reglas (tiempo reglamentario):
  - Acertar resultado (W/D/L o quien avanza)  -> 1 pt
  - + Diferencia de goles exacta              -> 1 pt adicional
  - + Marcador exacto                         -> 2 pts adicionales
  Maximo base: 4 pts

Eliminatorias con penales (cuando goles_local == goles_visita en tiempo reglamentario):
  - Acertar ganador en penales                -> ya cubierto por criterio 1 via penales_ganador
  - + Marcador exacto en penales              -> 1 pt adicional (con multiplicador)

Multiplicadores por fase:
  grupos / 16avos      -> x1
  octavos / cuartos    -> x2
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

    # Signo del resultado en tiempo reglamentario
    pred_res = (pred_local > pred_visita) - (pred_local < pred_visita)
    real_res = (real_local > real_visita) - (real_local < real_visita)

    # Para eliminatorias con penales: el resultado "real" es empate en tiempo
    # pero hay un ganador real en penales. El usuario debe predecir empate Y
    # el ganador correcto via sus penales.
    partido_fue_a_penales = (real_res == 0 and real_pen_local is not None
                             and real_pen_visita is not None)

    if partido_fue_a_penales:
        # Criterio 1: acerto que iriana penales (pred empate) Y acierta ganador en penales
        pred_tambien_empate = (pred_res == 0)
        if pred_tambien_empate:
            # Derivar ganador en penales predicho
            if pred_pen_local is not None and pred_pen_visita is not None:
                pred_gan_pen = 'local' if pred_pen_local > pred_pen_visita else 'visita'
            else:
                pred_gan_pen = None  # no ingreso penales -> no acierta

            real_gan_pen = 'local' if real_pen_local > real_pen_visita else 'visita'

            if pred_gan_pen == real_gan_pen:
                puntos += 1  # acierto resultado (via penales)

                if (pred_local - pred_visita) == (real_local - real_visita):
                    puntos += 1  # diferencia exacta en tiempo reglamentario

                    if pred_local == real_local and pred_visita == real_visita:
                        puntos += 2  # marcador exacto en tiempo reglamentario

                # Bonus: marcador exacto en penales
                if (pred_pen_local == real_pen_local
                        and pred_pen_visita == real_pen_visita):
                    puntos += 1
    else:
        # Partido normal (sin penales)
        if pred_res == real_res:
            puntos += 1  # acierto resultado

            if (pred_local - pred_visita) == (real_local - real_visita):
                puntos += 1  # diferencia exacta

                if pred_local == real_local and pred_visita == real_visita:
                    puntos += 2  # marcador exacto

    return puntos * multiplicador


# -- Recalcular puntos de un partido ya jugado ----------------------------

def recalcular_partido(partido_id: int) -> int:
    """
    Cuando se carga el resultado real de un partido, recalcula los puntos
    de todas las predicciones de ese partido y actualiza puntajes_fase.
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
