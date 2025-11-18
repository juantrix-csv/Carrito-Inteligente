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

        # Cache en memoria: nombre_super -> supermercado_id (INT, no el objeto)
        self.supermercados_cache = {}

    def get_or_create_supermercado(self, nombre, url=None, ciudad=None):
        """
        Devuelve el ID de un Supermercado a partir del nombre.
        Si no existe, lo crea. Usa un cache en memoria por performance.
        """
        # 1) Revisar cache (solo guardamos el ID)
        if nombre in self.supermercados_cache:
            supermercado_id = self.supermercados_cache[nombre]
            print(f"--------------------------- Usando supermercado cacheado: {nombre} (ID: {supermercado_id})")
            return supermercado_id

        # 2) Buscar en BD
        supermercado = Supermercado.query.filter_by(nombre=nombre).first()
        if not supermercado:
            supermercado = Supermercado(
                nombre=nombre,
                url=url,
                ciudad=ciudad
            )
            db.session.add(supermercado)
            db.session.commit()  # para que tenga ID

        supermercado_id = supermercado.id

        # 3) Guardar en cache (solo el ID)
        self.supermercados_cache[nombre] = supermercado_id
        print(f"--------------------------- Usando supermercado: {supermercado.nombre} (ID: {supermercado_id})")
        return supermercado_id

    def process_item(self, item, spider):
        with self.app.app_context():
            # ---- SUPERMERCADO ----
            nombre_super = item.get("supermercado_nombre", "Carrefour")
            url_super = item.get("supermercado_url", "https://www.carrefour.com.ar")
            ciudad_super = item.get("supermercado_ciudad")  # puede ser None

            supermercado_id = self.get_or_create_supermercado(
                nombre=nombre_super,
                url=url_super,
                ciudad=ciudad_super
            )

            # ---- PRODUCTO ----
            producto = Producto.query.filter_by(nombre=item["nombre"]).first()
            if not producto:
                producto = Producto(nombre=item["nombre"])
                db.session.add(producto)
                db.session.flush()
            print(f"Procesando producto: {producto.nombre} (ID: {producto.id})")

            # ---- PRODUCTO x SUPERMERCADO ----
            prod_super = ProductoSupermercado.query.filter_by(
                producto_id=producto.id,
                supermercado_id=supermercado_id
            ).first()

            if not prod_super:
                prod_super = ProductoSupermercado(
                    producto_id=producto.id,
                    supermercado_id=supermercado_id,
                    nombre_externo=item.get("nombre"),
                    codigo_externo=item.get("product_id"),
                    url=item.get("url"),
                    marca=item.get("marca"),
                    cantidad=item.get("multiplicador")
                )
                db.session.add(prod_super)
                db.session.flush()

            print(
                f"ProductoSupermercado ID: {prod_super.id} "
                f"para producto ID: {producto.id} en super {nombre_super}"
            )

            # ---- PRECIO ----
            precio = item.get("precio")
            if precio is not None:
                try:
                    precio_float = float(precio)
                except (TypeError, ValueError):
                    print(f"[WARN] Precio inválido para {producto.nombre}: {precio}")
                    precio_float = None

                if precio_float is not None:
                    precio_row = PrecioProducto(
                        producto_supermercado_id=prod_super.id,
                        precio=precio_float,
                        moneda="ARS",
                        fecha=date.today(),
                    )
                    db.session.add(precio_row)
                    print(
                        f"Precio registrado: {precio_float} para "
                        f"ProductoSupermercado ID: {prod_super.id} "
                        f"en {date.today()} ({nombre_super})"
                    )

            db.session.commit()

        return item
