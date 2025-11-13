from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from extensions import db 

def create_app():
    
    app = Flask(__name__)

    # Base de datos SQLite en un archivo local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///super_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    from models import Producto  # ajustá el import según tu estructura

    @app.route("/")
    def index():
        return "App andando con base de datos!"


    @app.route("/productos")
    def listar_productos():
        productos = Producto.query.all()
        return render_template("productos.html", productos=productos)



    return app
    
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)