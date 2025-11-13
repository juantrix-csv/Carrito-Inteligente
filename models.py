from app import db
from datetime import date

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)


class Supermercado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    ciudad = db.Column(db.String(100), nullable=True)


class ProductoSupermercado(db.Model):
    __tablename__ = "producto_supermercado"

    id = db.Column(db.Integer, primary_key=True)
    supermercado_id = db.Column(db.Integer, db.ForeignKey("supermercado.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    nombre_externo = db.Column(db.String(100), nullable=True)
    codigo_externo = db.Column(db.String(100), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    marca = db.Column(db.String(100), nullable=True)
    cantidad = db.Column(db.Integer, nullable=True)


class PrecioProducto(db.Model):
    __tablename__ = "precio_producto"

    id = db.Column(db.Integer, primary_key=True)
    producto_supermercado_id = db.Column(db.Integer, db.ForeignKey("producto_supermercado.id"), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(100), nullable=True)
    fecha = db.Column(db.Date, nullable=True, default=date.today)


class ListaCompra(db.Model):
    __tablename__ = "lista_compra"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.Date, nullable=False, default=date.today)


class ItemListaCompra(db.Model):
    __tablename__ = "item_lista_compra"

    id = db.Column(db.Integer, primary_key=True)
    lista_compra_id = db.Column(db.Integer, db.ForeignKey("lista_compra.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)