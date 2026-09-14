"""Factory de la aplicación Flask (patrón MVC)."""
import os
from pathlib import Path

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")

    data_dir = os.environ.get("REPORTES_DIR")
    if data_dir:
        app.config["DATA_DIR"] = Path(data_dir)
    else:
        app.config["DATA_DIR"] = Path.cwd() / "data" / "reportes"

    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)

    from reportes_app.controllers.main_controller import main_bp

    app.register_blueprint(main_bp)

    return app


def main() -> None:
    create_app().run(debug=True)
