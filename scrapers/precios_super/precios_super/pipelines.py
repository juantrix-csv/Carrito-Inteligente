import sys
import os

# ruta a la raíz del proyecto
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(ROOT_PATH)

from app import create_app, db
from models import Producto, Supermercado, ProductoSupermercado, PrecioProducto
from datetime import date

class DBPipeline:

    def __init__(self):
        # Crear app de Flask y activar contexto
        self.app = create_app()
        self.app.app_context().push()

        # Crear o buscar el supermercado Carrefour una sola vez
        self.supermercado = Supermercado.query.filter_by(nombre="Carrefour").first()
        if not self.supermercado:
            self.supermercado = Supermercado(
                nombre="Carrefour",
                url="https://www.carrefour.com.ar",
                ciudad=None
            )
            db.session.add(self.supermercado)
            db.session.commit()
        print(f"Usando supermercado: {self.supermercado.nombre} (ID: {self.supermercado.id})")

    def process_item(self, item, spider):
        with self.app.app_context():
            # 1) Crear o buscar Producto
            producto = Producto.query.filter_by(nombre=item["nombre"]).first()
            if not producto:
                producto = Producto(nombre=item["nombre"])
                db.session.add(producto)
                db.session.flush()
            print(f"Procesando producto: {producto.nombre} (ID: {producto.id})")

            # 2) Crear o buscar ProductoSupermercado
            prod_super = ProductoSupermercado.query.filter_by(
                producto_id=producto.id,
                supermercado_id=self.supermercado.id
            ).first()

            if not prod_super:
                prod_super = ProductoSupermercado(
                    producto_id=producto.id,
                    supermercado_id=self.supermercado.id,
                    nombre_externo=item.get("nombre"),
                    codigo_externo=item.get("product_id"),
                    url=item.get("url"),
                    marca=item.get("marca"),
                    cantidad=item.get("multiplicador")
                )
                db.session.add(prod_super)
                db.session.flush()
            print(f"ProductoSupermercado ID: {prod_super.id} para producto ID: {producto.id}")

            # 3) Insertar precio del día
            precio = item.get("precio")
            if precio is not None:
                precio_row = PrecioProducto(
                    producto_supermercado_id=prod_super.id,
                    precio=float(precio),
                    moneda="ARS",
                    fecha=date.today(),
                )
                db.session.add(precio_row)

            db.session.commit()
            print(f"Precio registrado: {precio} para ProductoSupermercado ID: {prod_super.id} en {date.today()}")
        return item
