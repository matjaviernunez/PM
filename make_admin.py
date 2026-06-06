"""make_admin.py — Da permisos de admin a un usuario."""
from db import get_db

username = input("Username a hacer admin: ").strip()
with get_db() as conn:
    r = conn.execute("UPDATE usuarios SET es_admin=TRUE WHERE username=?", (username,))
    conn.commit()
    if r.rowcount:
        print(f"✓ {username} ahora es admin")
    else:
        print("Usuario no encontrado")
