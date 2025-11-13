from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Base de datos SQLite en un archivo local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///super_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Importás los modelos acá si están en otro archivo
    # from .models import Producto

    @app.route("/")
    def index():
        return "App andando con base de datos!"

    return app
