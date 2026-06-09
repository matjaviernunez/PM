"""
game/bracket.py -- Posiciones de grupo y logica de eliminatorias.

Task #10: get_tabla_grupo(), get_clasificados(), _get_mejores_terceros()
Task #12: generar_cruces_16avos(), get_cruces_16avos()
"""

from db import get_db
from config import GRUPOS


# =====================================================================
#  POSICIONES DE GRUPOS
# =====================================================================

def get_tabla_grupo(grupo):
    """
    Calcula la tabla de posiciones de un grupo a partir de los
    resultados reales ya cargados en la tabla partidos.
    Retorna lista de 4 equipos ordenada por pts -> DG -> GF -> alfa.
    """
    with get_db() as conn:
        equipos_raw = conn.execute("""
            SELECT DISTINCT equipo_local AS equipo
            FROM partidos WHERE fase = 'grupos' AND grupo = ?
            UNION
            SELECT DISTINCT equipo_visita
            FROM partidos WHERE fase = 'grupos' AND grupo = ?
        """, (grupo, grupo)).fetchall()

        partidos = conn.execute("""
            SELECT equipo_local, equipo_visita, goles_local, goles_visita
            FROM partidos
            WHERE fase = 'grupos' AND grupo = ? AND goles_local IS NOT NULL
        """, (grupo,)).fetchall()

    stats = {
        r["equipo"]: {
            "equipo": r["equipo"], "grupo": grupo,
            "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "dg": 0, "pts": 0,
        }
        for r in equipos_raw
    }

    for p in partidos:
        lo, vi = p["equipo_local"], p["equipo_visita"]
        gl, gv = p["goles_local"],  p["goles_visita"]

        for e in (lo, vi):
            stats[e]["pj"] += 1

        stats[lo]["gf"] += gl;  stats[lo]["gc"] += gv
        stats[vi]["gf"] += gv;  stats[vi]["gc"] += gl

        if gl > gv:
            stats[lo]["pg"] += 1;  stats[lo]["pts"] += 3
            stats[vi]["pp"] += 1
        elif gl == gv:
            stats[lo]["pe"] += 1;  stats[lo]["pts"] += 1
            stats[vi]["pe"] += 1;  stats[vi]["pts"] += 1
        else:
            stats[vi]["pg"] += 1;  stats[vi]["pts"] += 3
            stats[lo]["pp"] += 1

    for e in stats.values():
        e["dg"] = e["gf"] - e["gc"]

    tabla = sorted(
        stats.values(),
        key=lambda x: (-x["pts"], -x["dg"], -x["gf"], x["equipo"]),
    )
    for i, row in enumerate(tabla):
        row["pos"] = i + 1

    return tabla


def get_todas_tablas():
    """Retorna {grupo: tabla} para los 12 grupos."""
    return {g: get_tabla_grupo(g) for g in GRUPOS}


# =====================================================================
#  CLASIFICADOS + MEJORES TERCEROS  (Task #10)
# =====================================================================

def get_clasificados():
    """
    Retorna:
      tablas           -> {grupo: [4 filas]}
      primeros         -> [hasta 12 ganadores]
      segundos         -> [hasta 12 subcampeones]
      terceros         -> [hasta 12 terceros]
      mejores_terceros -> [8 mejores terceros, campo 'slot' 1-8]
    """
    tablas = {}
    primeros, segundos, terceros = [], [], []

    for grupo in GRUPOS:
        tabla = get_tabla_grupo(grupo)
        tablas[grupo] = tabla
        if len(tabla) >= 1: primeros.append(tabla[0])
        if len(tabla) >= 2: segundos.append(tabla[1])
        if len(tabla) >= 3: terceros.append(tabla[2])

    mejores = _get_mejores_terceros(terceros)

    return {
        "tablas":           tablas,
        "primeros":         primeros,
        "segundos":         segundos,
        "terceros":         terceros,
        "mejores_terceros": mejores,
    }


def _get_mejores_terceros(terceros):
    """
    De los 12 terceros selecciona los 8 mejores segun criterios FIFA:
    1. Puntos  2. DG  3. GF  4. Alfabetico
    """
    ranked = sorted(
        terceros,
        key=lambda x: (-x["pts"], -x["dg"], -x["gf"], x["equipo"]),
    )
    mejores = ranked[:8]
    for i, t in enumerate(mejores):
        t["slot"] = i + 1
    return mejores


# =====================================================================
#  BRACKET FIFA 2026  (Task #12)
# =====================================================================
#
# 16 partidos de 16avos:
#   M01-M08 : Ganador grupo A-H  vs  Mejor tercero (anti-clash)
#   M09-M12 : Subcampeones A/B, C/D, E/F, G/H entre si
#   M13-M16 : Ganadores I-L  vs  Subcampeones cruzados (I<->L, J<->K)
#
# Slots: '1X' = ganador grupo X  |  '2X' = subcampeon grupo X
#        '3T' = mejor tercero (se resuelve con anti-clash)
# ---------------------------------------------------------------------

BRACKET_TEMPLATE = [
    # (num, local_slot, visita_slot)
    ( 1, "1A", "3T"),
    ( 2, "1B", "3T"),
    ( 3, "1C", "3T"),
    ( 4, "1D", "3T"),
    ( 5, "1E", "3T"),
    ( 6, "1F", "3T"),
    ( 7, "1G", "3T"),
    ( 8, "1H", "3T"),
    ( 9, "2A", "2B"),
    (10, "2C", "2D"),
    (11, "2E", "2F"),
    (12, "2G", "2H"),
    (13, "1I", "2L"),
    (14, "1J", "2K"),
    (15, "1K", "2J"),
    (16, "1L", "2I"),
]

# Fechas y horas tentativas (FIFA 2026 aprox 27 jun - 2 jul)
FECHAS_16AVOS = [
    "2026-06-27", "2026-06-27",
    "2026-06-28", "2026-06-28",
    "2026-06-29", "2026-06-29",
    "2026-06-30", "2026-06-30",
    "2026-07-01", "2026-07-01",
    "2026-07-01", "2026-07-01",
    "2026-07-02", "2026-07-02",
    "2026-07-02", "2026-07-02",
]

HORAS_16AVOS = [
    "15:00", "19:00",
    "15:00", "19:00",
    "15:00", "19:00",
    "15:00", "19:00",
    "13:00", "17:00",
    "13:00", "17:00",
    "13:00", "17:00",
    "13:00", "17:00",
]


def _asignar_terceros(mejores):
    """
    Asigna los 8 mejores terceros a los slots M01-M08 (ganadores A-H)
    evitando que un tercero enfrente al 1ro de su propio grupo.
    Devuelve lista de 8 codigos (o placeholder si aun no hay equipo).
    """
    winner_groups = list("ABCDEFGH")
    pendientes    = list(mejores)
    asignados     = [None] * 8

    # Pasada 1: asignar evitando mismo grupo
    for i, wg in enumerate(winner_groups):
        for j, t in enumerate(pendientes):
            if t["grupo"] != wg:
                asignados[i] = t["equipo"]
                pendientes.pop(j)
                break

    # Pasada 2: forzar los que quedan si hay huecos
    for i in range(8):
        if asignados[i] is None and pendientes:
            asignados[i] = pendientes.pop(0)["equipo"]

    # Placeholder para slots sin equipo todavia
    for i in range(8):
        if asignados[i] is None:
            asignados[i] = "3T{}".format(i + 1)

    return asignados


def _resolver_slot(slot, primeros, segundos):
    """'1A' -> codigo equipo ganador A (o el slot literal si aun no hay resultado)."""
    if slot.startswith("1"):
        grupo = slot[1:]
        m = next((e for e in primeros if e["grupo"] == grupo), None)
        return m["equipo"] if m else slot
    if slot.startswith("2"):
        grupo = slot[1:]
        m = next((e for e in segundos if e["grupo"] == grupo), None)
        return m["equipo"] if m else slot
    return slot


def generar_cruces_16avos():
    """
    Inserta los 16 partidos de 16avos en la tabla partidos.
    Idempotente: si ya existen, no hace nada.
    """
    with get_db() as conn:
        ya = conn.execute(
            "SELECT COUNT(*) AS n FROM partidos WHERE fase = '16avos'"
        ).fetchone()["n"]
        if ya > 0:
            return {
                "ok": False,
                "mensaje": "Ya existen {} partidos de 16avos. Borralos desde la DB para regenerar.".format(ya),
            }

        clasi    = get_clasificados()
        primeros = clasi["primeros"]
        segundos = clasi["segundos"]
        mejores  = clasi["mejores_terceros"]

        terceros_slots = _asignar_terceros(mejores)
        t3_idx = 0

        for i, (num, local_slot, visita_slot) in enumerate(BRACKET_TEMPLATE):
            fecha = FECHAS_16AVOS[i] if i < len(FECHAS_16AVOS) else "2026-06-27"
            hora  = HORAS_16AVOS[i]  if i < len(HORAS_16AVOS)  else "18:00"

            if visita_slot == "3T":
                local  = _resolver_slot(local_slot, primeros, segundos)
                visita = terceros_slots[t3_idx] if t3_idx < 8 else "3T{}".format(t3_idx + 1)
                t3_idx += 1
            else:
                local  = _resolver_slot(local_slot, primeros, segundos)
                visita = _resolver_slot(visita_slot, primeros, segundos)

            conn.execute("""
                INSERT INTO partidos
                    (fase, grupo, fecha, hora, equipo_local, equipo_visita, abierto)
                VALUES ('16avos', NULL, ?, ?, ?, ?, TRUE)
            """, (fecha, hora, local, visita))

        conn.commit()

    return {"ok": True, "creados": 16, "mensaje": "16 partidos de 16avos generados."}


def get_cruces_16avos():
    """Retorna los 16 partidos de 16avos con su estado actual."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM partidos
            WHERE fase = '16avos'
            ORDER BY fecha, hora, id
        """).fetchall()
    return [dict(r) for r in rows]
