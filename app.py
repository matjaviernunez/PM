from flask import Flask, redirect, url_for
from flask_login import LoginManager
import config

# ── Inicialización Flask ───────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = config.SECRET_KEY
app.debug      = config.DEBUG

# ── Flask-Login ────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesión para acceder."

@login_manager.user_loader
def load_user(user_id):
    from auth.models import Usuario
    return Usuario.get_by_id(int(user_id))

# ── Blueprints ─────────────────────────────────────────────────────────────
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

# ── Rutas base ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for("predicciones.index"))
    return redirect(url_for("auth.login"))

# ── Filtros Jinja ──────────────────────────────────────────────────────────
app.jinja_env.globals["enumerate"] = enumerate

if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)
