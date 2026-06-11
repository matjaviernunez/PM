import logging
from flask import Flask, redirect, url_for
from flask_login import LoginManager
import config

logging.basicConfig(level=logging.INFO)

# -- Inicializacion Flask --------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = config.SECRET_KEY
app.debug      = config.DEBUG

# -- Flask-Login -----------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesion para acceder."

@login_manager.user_loader
def load_user(user_id):
    from auth.models import Usuario
    return Usuario.get_by_id(int(user_id))

# -- Blueprints ------------------------------------------------------------
from auth.routes import auth_bp
app.register_blueprint(auth_bp, url_prefix="/auth")

from admin.routes import admin_bp
app.register_blueprint(admin_bp, url_prefix="/admin")

from predicciones.routes import pred_bp
app.register_blueprint(pred_bp, url_prefix="/predicciones")

from ranking.routes import ranking_bp
app.register_blueprint(ranking_bp, url_prefix="/ranking")

from hub.routes import hub_bp
app.register_blueprint(hub_bp, url_prefix="/mundial")

from torneo.routes import torneo_bp
app.register_blueprint(torneo_bp, url_prefix="/torneo")

# -- Rutas base ------------------------------------------------------------
@app.route("/")
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for("predicciones.index"))
    return redirect(url_for("auth.login"))

# -- Migración: ultima_posicion --------------------------------------------
from db import get_db as _get_db
with _get_db() as _conn:
    try:
        _conn.execute("ALTER TABLE usuarios ADD COLUMN ultima_posicion INTEGER DEFAULT NULL")
        _conn.commit()
    except Exception:
        pass  # columna ya existe

# -- Context processor: ranking popup --------------------------------------
from flask import session as _flask_session
@app.context_processor
def _inject_ranking_popup():
    return {'ranking_popup': _flask_session.pop('ranking_popup', None)}

# -- Globals Jinja ---------------------------------------------------------
app.jinja_env.globals["enumerate"] = enumerate

def _slot_label(slot):
    """Convierte slots del bracket en texto legible para el template."""
    if not slot:
        return "TBD"
    if len(slot) == 2 and slot[0] == "1":
        return "1 Gr. {}".format(slot[1])
    if len(slot) == 2 and slot[0] == "2":
        return "2 Gr. {}".format(slot[1])
    if slot.startswith("3T"):
        return "Mejor 3ro"
    return slot

app.jinja_env.globals["_slot_label"] = _slot_label

# -- Scheduler: sincronizar resultados ESPN cada 60 s ---------------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from game.espn_sync import sync_scores

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(sync_scores, 'interval', seconds=60, id='espn_sync',
                       misfire_grace_time=30)
    _scheduler.start()
    logging.getLogger(__name__).info('ESPN sync scheduler iniciado (cada 60 s)')
except Exception as _e:
    logging.getLogger(__name__).warning('No se pudo iniciar el scheduler: %s', _e)

if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)
