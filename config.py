import os

# ── Rutas ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables desde .env (si existe). Antes no se cargaba, por lo que en
# producción SECRET_KEY y DEBUG se quedaban en sus defaults de desarrollo.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass  # python-dotenv no instalado: se usan las variables del entorno tal cual

# En Railway el volumen se monta en /data — configurable via env var
_db_dir  = os.environ.get("DB_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH  = os.path.join(_db_dir, "mundial2026.db")

# ── Flask ──────────────────────────────────────────────────────────────────
# DEBUG por defecto en FALSE: en producción el debugger de Werkzeug es un riesgo
# de ejecución remota. Para desarrollo local, poner DEBUG=true en el .env.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-SOLO-LOCAL-cambiar-en-produccion")
DEBUG      = os.environ.get("DEBUG", "false").lower() == "true"

# ── Scraper ────────────────────────────────────────────────────────────────
SCRAPER_INTERVAL_LIVE    = 120   # segundos — durante un partido activo
SCRAPER_INTERVAL_IDLE    = 3600  # segundos — fuera de partidos
SCRAPER_SOURCE_URL       = "https://www.sofascore.com"  # ajustar según fuente elegida

# ── Torneo ─────────────────────────────────────────────────────────────────
FASES = ["grupos", "16avos", "octavos", "cuartos", "semis", "3er_puesto", "final"]

MULTIPLICADORES = {
    "grupos":      1,
    "16avos":      1,
    "octavos":     2,
    "cuartos":     2,
    "semis":       3,
    "3er_puesto":  3,
    "final":       3,
}

GRUPOS = list("ABCDEFGHIJKL")  # 12 grupos para 2026

# ── Admin ──────────────────────────────────────────────────────────────────
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "javier.ns87@gmail.com")
