"""
game/models.py — Queries de partidos y predicciones.
"""

from datetime import datetime, date
from db import get_db


# ── Partidos ───────────────────────────────────────────────────────────────

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


def guardar_predicciones_lote(usuario_id: int, predicciones: list[dict]) -> dict:
    """
    Guarda múltiples predicciones de una vez.
    predicciones: [{partido_id, goles_local, goles_visita}, ...]
    Retorna {guardados: N, cerrados: N}
    """
    guardados = 0
    cerrados  = 0
    for p in predicciones:
        ok = guardar_prediccion(
            usuario_id=usuario_id,
            partido_id=p["partido_id"],
            goles_local=p["goles_local"],
            goles_visita=p["goles_visita"],
        )
        if ok:
            guardados += 1
        else:
            cerrados += 1
    return {"guardados": guardados, "cerrados": cerrados}


def cerrar_partidos_vencidos():
    """Marca como cerrados los partidos cuya fecha/hora ya pasó."""
    ahora = datetime.now()
    with get_db() as conn:
        conn.execute("""
            UPDATE partidos
            SET abierto = FALSE
            WHERE abierto = TRUE
              AND datetime(fecha || ' ' || hora) <= ?
        """, (ahora.strftime("%Y-%m-%d %H:%M"),))
        conn.commit()


# ── Predicciones ───────────────────────────────────────────────────────────

def get_predicciones_usuario(usuario_id: int, partido_ids: list[int]) -> dict:
    """
    Retorna un dict {partido_id: prediccion_dict} para los partidos dados.
    """
    if not partido_ids:
        return {}
    placeholders = ",".join("?" * len(partido_ids))
    with get_db() as conn:
        rows = conn.execute(f"""
            SELECT * FROM predicciones
            WHERE usuario_id = ? AND partido_id IN ({placeholders})
        """, (usuario_id, *partido_ids)).fetchall()
    return {r["partido_id"]: dict(r) for r in rows}


def guardar_prediccion(usuario_id: int, partido_id: int,
                       goles_local: int, goles_visita: int,
                       penales_ganador: str = None) -> bool:
    """
    Inserta o actualiza una predicción.
    Retorna False si el partido ya cerró.
    """
    with get_db() as conn:
        partido = conn.execute(
            "SELECT abierto FROM partidos WHERE id = ?", (partido_id,)
        ).fetchone()

        if not partido or not partido["abierto"]:
            return False

        conn.execute("""
            INSERT INTO predicciones
                (usuario_id, partido_id, goles_local, goles_visita, penales_ganador)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(usuario_id, partido_id) DO UPDATE SET
                goles_local     = excluded.goles_local,
                goles_visita    = excluded.goles_visita,
                penales_ganador = excluded.penales_ganador
        """, (usuario_id, partido_id, goles_local, goles_visita, penales_ganador))
        conn.commit()
    return True
