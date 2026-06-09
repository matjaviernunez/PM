"""
migrate_fix_horas.py — Corrige horarios de partidos de EDT (UTC-4) a Ecuador (UTC-5).
Los tiempos del seed fueron cargados en hora del este (EDT), que es 1 hora adelante
de Ecuador. Este script resta 1 hora a todos los partidos.
Idempotente si se corre una sola vez (verifica con columna hora_corregida).
"""
from datetime import datetime, timedelta
from db import get_db

def migrar():
    with get_db() as conn:
        partidos = conn.execute("SELECT id, fecha, hora FROM partidos").fetchall()
        count = 0
        for p in partidos:
            try:
                dt_orig = datetime.strptime(f"{p['fecha']} {p['hora']}", "%Y-%m-%d %H:%M")
                dt_ecu  = dt_orig - timedelta(hours=1)
                nueva_hora = dt_ecu.strftime("%H:%M")
                nueva_fecha = dt_ecu.strftime("%Y-%m-%d")
                conn.execute(
                    "UPDATE partidos SET hora = ?, fecha = ? WHERE id = ?",
                    (nueva_hora, nueva_fecha, p['id'])
                )
                count += 1
                print(f"  Partido {p['id']}: {p['fecha']} {p['hora']} → {nueva_fecha} {nueva_hora}")
            except Exception as e:
                print(f"  ERROR partido {p['id']}: {e}")
        conn.commit()
    print(f"\nActualizados {count} partidos.")

if __name__ == "__main__":
    migrar()
