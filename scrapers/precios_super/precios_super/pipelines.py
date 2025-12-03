import sys
import os
# ruta a la raíz del proyecto
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(ROOT_PATH)

from utils.embedding import embed, encontrar_producto_por_nombre_semantico
from utils.normalizar import normalizar
from app import create_app, db
from models import Producto, Supermercado, ProductoSupermercado, PrecioProducto, Marca
from datetime import date

class DBPipeline:

    def __init__(self):
        # Crear app de Flask y activar contexto
        self.app = create_app()
        self.app.app_context().push()

        # Cache en memoria: nombre_super -> supermercado_id (INT, no el objeto)
        self.supermercados_cache = {}

    def process_unit_value(self, text): # TODO implementar para normalizar unidades y valores
        pass

    def process_marca(self, text): # TODO: mejorar esta funcion con embeddings
        """
        Procesa el nombre de una marca.
        Si la marca ya existe en la DB (incluso como sinónimo), devuelve el
        nombre de la marca existente.
        Si no existe, crea un nuevo registro de Marca y devuelve su nombre.
        Si no se puede determinar una marca válida, devuelve None.
        """
        marca_aislada = not(" " in text and len(text.split(" ")) > 1)
        if marca_aislada:
            # comprobar si text es una marca existente en la db   
            marca_existe = Marca.query.filter(Marca.sinonimos.contains([text])).first()
            if marca_existe:
                return text
            # crear registro en la DB de nueva marca
            new_marca = Marca(
                nombre=text,
                sinonimos=[text]
            )
            db.session.add(new_marca)
            db.session.commit()
            return text

        for word in text.split(" "):
            # comprobar si word es una marca existente en la db
            marca_existe = Marca.query.filter(Marca.sinonimos.contains([word])).first()
            if marca_existe:
                return word
            
        # logear: No se encontro coincidencia con las marcas de la DB.
        print(f"[WARN] No se encontro coincidencia de marca para: {text}")
        return None
    
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
        """
        Procesa un item extraído por un spider.
        Guarda/actualiza la información en la base de datos.
        Retorna el item procesado.
        """
        with self.app.app_context():
            # ---- SUPERMERCADO ----
            nombre_super = item.get("supermercado_nombre", None)
            url_super = item.get("supermercado_url", None)
            ciudad_super = item.get("supermercado_ciudad", None)  # puede ser None

            if not nombre_super:
                print("[ERROR] El item no tiene 'supermercado_nombre'. No se puede procesar.")
                return item
            if not url_super:
                print("[ERROR] El item no tiene 'supermercado_url'. No se puede procesar.")
                return item

            supermercado_id = self.get_or_create_supermercado(
                nombre=nombre_super,
                url=url_super,
                ciudad=ciudad_super
            )

            # ---- PRODUCTO ----
            # producto = Producto.query.filter_by(nombre=item["nombre"]).first()
            marca = self.process_marca(item.get("marca"))
            producto, sim = encontrar_producto_por_nombre_semantico(item["nombre"], marca)
            if not producto or sim < 0.85:
                producto = Producto(
                    nombre=item["nombre"],
                    embedding=embed(item["nombre"]),
                    marca_id=Marca.query.filter_by(nombre=marca).first().id if marca else None,
                    unidad_medida=item.get("unidad"),
                    valor_medida=item.get("multiplicador")
                )
                db.session.add(producto)
                db.session.flush()
            print(f"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX   Procesando producto: {producto.nombre} (ID: {producto.id})")

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
                    marca=marca,
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

            # ---- normalizar y commit ----
            normalizar(item["nombre"])

            db.session.commit()

        return item

