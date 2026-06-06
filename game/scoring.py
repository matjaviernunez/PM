"""
game/scoring.py — Motor de puntuación de la polla.

Reglas:
  - Acertar resultado (W/D/L)          → 1 pt
  - + Diferencia de goles exacta        → 1 pt adicional
  - + Marcador exacto                   → 2 pts adicionales
  - Máximo sin multiplicador            → 4 pts

Multiplicadores por fase:
  grupos / 16avos  → ×1
  octavos / cuartos → ×2
  semis / 3er_puesto / final → ×3
"""

from db import get_db
from config import MULTIPLICADORES


# ── Cálculo de puntos para un partido ─────────────────────────────────────

def calcular_puntos(
    pred_local: int, pred_visita: int,
    real_local: int, real_visita: int,
    fase: str,
) -> int:
    multiplicador = MULTIPLICADORES.get(fase, 1)
    puntos = 0

    # Signo del resultado: +1 local gana, 0 empate, -1 visita gana
    pred_res = (pred_local > pred_visita) - (pred_local < pred_visita)
    real_res = (real_local > real_visita) - (real_local < real_visita)

    if pred_res == real_res:
        puntos += 1  # acertó resultado

        if (pred_local - pred_visita) == (real_local - real_visita):
            puntos += 1  # acertó diferencia de goles

            if pred_local == real_local and pred_visita == real_visita:
                puntos += 2  # acertó marcador exacto

    return puntos * multiplicador


# ── Recalcular puntos de un partido ya jugado ──────────────────────────────

def recalcular_partido(partido_id: int) -> int:
    """
    Cuando se carga el resultado real de un partido, recalcula los puntos
    de todas las predicciones de ese partido y actualiza puntajes_fase.
    Retorna el número de predicciones procesadas.
    """
    with get_db() as conn:
        partido = conn.execute(
            "SELECT * FROM partidos WHERE id = ?", (partido_id,)
        ).fetchone()

        if not partido:
            return 0
        if partido["goles_local"] is None or partido["goles_visita"] is None:
            return 0  # resultado aún no cargado

        predicciones = conn.execute(
            "SELECT * FROM predicciones WHERE partido_id = ?", (partido_id,)
        ).fetchall()

        procesadas = 0
        for pred in predicciones:
            puntos = calcular_puntos(
                pred_local=pred["goles_local"],
                pred_visita=pred["goles_visita"],
                real_local=partido["goles_local"],
                real_visita=partido["goles_visita"],
                fase=partido["fase"],
            )

            # Actualizar puntos en predicciones
            conn.execute(
                "UPDATE predicciones SET puntos_obtenidos = ? WHERE id = ?",
                (puntos, pred["id"])
            )

            # Upsert en puntajes_fase
            conn.execute("""
                INSERT INTO puntajes_fase (usuario_id, fase, puntos)
                VALUES (?, ?, ?)
                ON CONFLICT(usuario_id, fase) DO UPDATE SET
                    puntos = puntos + excluded.puntos
            """, (pred["usuario_id"], partido["fase"], puntos))

            procesadas += 1

        conn.commit()
    return procesadas


# ── Ranking general ────────────────────────────────────────────────────────

def get_ranking(liga_id: int = None) -> list[dict]:
    """
    Retorna lista de {usuario_id, nickname, codigo, total, por_fase}
    ordenada por puntos desc.
    Si liga_id es None devuelve todos (ranking global).
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
                "SELECT id, nickname, codigo, equipo_favorito, campeon_favorito FROM usuarios"
            ).fetchall()

        ranking = []
        for u in usuarios:
            fases = conn.execute("""
                SELECT fase, puntos FROM puntajes_fase WHERE usuario_id = ?
            """, (u["id"],)).fetchall()

            por_fase = {f["fase"]: f["puntos"] for f in fases}
            total = sum(por_fase.values())

            # Aciertos exactos (para desempate)
            exactos = conn.execute("""
                SELECT COUNT(*) as n FROM predicciones
                WHERE usuario_id = ? AND puntos_obtenidos IS NOT NULL
                  AND goles_local = (
                      SELECT goles_local FROM partidos WHERE id = partido_id
                  )
                  AND goles_visita = (
                      SELECT goles_visita FROM partidos WHERE id = partido_id
                  )
            """, (u["id"],)).fetchone()["n"]

            ranking.append({
                "usuario_id":      u["id"],
                "nickname":        u["nickname"],
                "codigo":          u["codigo"],
                "equipo_favorito": u["equipo_favorito"],
                "campeon_favorito":u["campeon_favorito"],
                "total":           total,
                "por_fase":        por_fase,
                "exactos":         exactos,
            })

        # Ordenar: total desc → exactos desc → nickname asc
        ranking.sort(key=lambda x: (-x["total"], -x["exactos"], x["nickname"]))

    return ranking
