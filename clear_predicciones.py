"""Borra todas las predicciones guardadas (para pruebas)."""
from db import get_db
with get_db() as conn:
    conn.execute("DELETE FROM predicciones")
    conn.commit()
    print("✓ Predicciones borradas")
