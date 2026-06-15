"""
backup_db.py -- Respaldo consistente de la DB (SQLite) con rotacion.

Crea data/backups/mundial2026_AAAAMMDD_HHMM.db usando la API de backup de
SQLite, que produce un snapshot consistente AUNQUE la DB este en uso con WAL
(un 'cp' crudo podria capturar un estado a medias). Conserva los ultimos KEEP.

Uso:  python backup_db.py
Ideal como Tarea Programada diaria en PythonAnywhere, o a mano antes de un
deploy/migracion riesgosa.
"""

import os
import glob
import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH

KEEP = 14  # cuantos snapshots conservar


def _backups_dir() -> str:
    d = os.path.join(os.path.dirname(DB_PATH), "backups")
    os.makedirs(d, exist_ok=True)
    return d


def hacer_backup(dest_dir: str = None) -> str:
    """Crea un snapshot consistente y retorna su ruta."""
    dest_dir = dest_dir or _backups_dir()
    ts = (datetime.utcnow() - timedelta(hours=5)).strftime("%Y%m%d_%H%M")  # ECT
    dest = os.path.join(dest_dir, f"mundial2026_{ts}.db")

    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)   # API de backup online de SQLite
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def rotar(dest_dir: str = None, keep: int = KEEP) -> int:
    """Borra los snapshots mas viejos, conservando los 'keep' mas recientes."""
    dest_dir = dest_dir or _backups_dir()
    archivos = sorted(glob.glob(os.path.join(dest_dir, "mundial2026_*.db")))
    sobran = archivos[:-keep] if len(archivos) > keep else []
    for f in sobran:
        try:
            os.remove(f)
        except OSError:
            pass
    return len(sobran)


if __name__ == "__main__":
    ruta = hacer_backup()
    borrados = rotar()
    print(f"Backup creado: {ruta}")
    print(f"Snapshots viejos eliminados: {borrados} (se conservan {KEEP})")
