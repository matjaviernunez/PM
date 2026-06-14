"""
migrate_normaliza_estado.py -- Sanea la columna 'estado' de partidos.

Marca estado='post' en los partidos que YA terminaron y tienen resultado,
pero que quedaron con estado distinto de 'post' (tipicamente 'in', porque
cerrar_partidos_vencidos los paso de 'pre' a 'in' al empezar y nunca
avanzaron a 'post').

Regla de "terminado": kickoff (fecha+hora en hora Ecuador) + 150 min < ahora.

Es idempotente: se puede correr varias veces sin efecto adicional.
Uso en PythonAnywhere:  python migrate_normaliza_estado.py
"""

from datetime import datetime, timedelta
from db import get_db

DUR_PARTIDO_MIN = 150  # misma ventana que game.models.estado_partido


def normaliza():
    ahora_ect = datetime.utcnow() - timedelta(hours=5)  # hora Ecuador UTC-5
    umbral = (ahora_ect - timedelta(minutes=DUR_PARTIDO_MIN)).strftime('%Y-%m-%d %H:%M')

    with get_db() as conn:
        # Listar antes (para reporte)
        afectados = conn.execute("""
            SELECT id, equipo_local, equipo_visita, fecha, hora, estado,
                   goles_local, goles_visita
            FROM partidos
            WHERE (estado IS NULL OR estado != 'post')
              AND goles_local IS NOT NULL
              AND hora IS NOT NULL AND hora != ''
              AND datetime(fecha || ' ' || hora) <= datetime(?)
        """, (umbral,)).fetchall()

        cur = conn.execute("""
            UPDATE partidos
            SET estado = 'post'
            WHERE (estado IS NULL OR estado != 'post')
              AND goles_local IS NOT NULL
              AND hora IS NOT NULL AND hora != ''
              AND datetime(fecha || ' ' || hora) <= datetime(?)
        """, (umbral,))
        n = cur.rowcount
        conn.commit()

    print(f"Umbral (kickoff <=): {umbral} ECT")
    print(f"Partidos normalizados a estado='post': {n}")
    for p in afectados:
        print(f"  id={p['id']} {p['equipo_local']} {p['goles_local']}-{p['goles_visita']} "
              f"{p['equipo_visita']}  {p['fecha']} {p['hora']}  (estado previo: {p['estado']})")
    if n == 0:
        print("Nada que normalizar.")


if __name__ == '__main__':
    normaliza()
