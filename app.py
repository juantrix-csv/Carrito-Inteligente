from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from extensions import db 
import json 
def create_app():
    
    app = Flask(__name__)

    # Base de datos SQLite en un archivo local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///super_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = "cambia_esta_clave_por_una_muy_larga_y_aleatoria_123456789"
    db.init_app(app)
    from models import Producto, ListaCompra, PrecioProducto, ProductoSupermercado, Supermercado, ItemListaCompra  # ajustá el import según tu estructura

    @app.route('/lista/')
    def lista_compra_home():
        listas = ListaCompra.query.order_by(ListaCompra.fecha_creacion.desc()).all()
        lista_activa = None
        if 'lista_activa_id' in session:
            lista_activa = ListaCompra.query.get(session['lista_activa_id'])
        return render_template('lista_compra.html', listas=listas, lista_activa=lista_activa)

    @app.route('/lista/crear', methods=['POST'])
    def crear_lista():
        nombre = request.form['nombre'].strip()
        if not nombre:
            return "Nombre requerido", 400
        lista = ListaCompra(nombre=nombre)
        db.session.add(lista)
        db.session.commit()
        session['lista_activa_id'] = lista.id
        return render_template('partials/lista_activa.html', lista_activa=lista)

    @app.route('/lista/<int:lista_id>')
    def ver_lista(lista_id):
        lista = ListaCompra.query.get_or_404(lista_id)
        session['lista_activa_id'] = lista.id
        return redirect(url_for('lista_compra_home'))

    @app.route('/api/buscar')
    def buscar_productos():
        q = request.args.get('query', '').strip()
        if len(q) < 2:
            return ''

        resultados = db.session.query(
            Producto, PrecioProducto.precio, Supermercado.nombre
        ).join(ProductoSupermercado, Producto.id == ProductoSupermercado.producto_id
        ).join(PrecioProducto, PrecioProducto.producto_supermercado_id == ProductoSupermercado.id
        ).join(Supermercado, Supermercado.id == ProductoSupermercado.supermercado_id
        ).filter(Producto.nombre.ilike(f'%{q}%')
        ).order_by(PrecioProducto.precio.asc()
        ).limit(10).all()

        if not resultados:
            return '<div class="p-3 text-muted">No se encontraron productos</div>'

        html = '<div class="autocomplete-suggestions shadow-lg bg-white rounded border" style="max-height:400px;overflow-y:auto;">'
        
        for prod, precio, supermercado in resultados:
            # Todo convertido a JSON válido
            nombre_js = json.dumps(prod.nombre or "Sin nombre")
            super_js = json.dumps(supermercado or "Desconocido")
            precio_js = round(float(precio), 2) if precio else 0
            
            html += f'''
            <div class="px-3 py-3 border-bottom" style="cursor:pointer;background:var(--bs-light);"
                onclick='seleccionarProducto({prod.id}, {nombre_js}, {precio_js}, {super_js})'>
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{prod.nombre}</strong><br>
                        <small class="text-muted">{supermercado}</small>
                    </div>
                    <div class="text-success fw-bold">
                        ${precio_js if precio_js else "Sin precio"}
                    </div>
                </div>
            </div>
            '''
        html += '</div>'
        return html

    @app.route('/listas/<int:lista_id>/agregar', methods=['POST'])
    def agregar_item(lista_id):
        lista = ListaCompra.query.get_or_404(lista_id)

        producto_id = request.form.get('producto_id', type=int)
        cantidad = request.form.get('cantidad', type=int, default=1)

        if not producto_id:
            # Si no seleccionaron producto de las sugerencias, no hacemos nada raro
            return cargar_items(lista)

        item = ItemListaCompra.query.filter_by(
            lista_compra_id=lista.id,
            producto_id=producto_id
        ).first()

        if item:
            item.cantidad += cantidad
        else:
            item = ItemListaCompra(
                lista_compra_id=lista.id,
                producto_id=producto_id,
                cantidad=cantidad
            )
            db.session.add(item)

        db.session.commit()
        return cargar_items(lista)

    @app.route('/item/<int:item_id>/quitar', methods=['POST'])
    def quitar_item(item_id):
        # Buscar el item
        item = ItemListaCompra.query.get_or_404(item_id)
        
        # Recuperar la lista completa (objeto), no solo el ID
        lista = ListaCompra.query.get_or_404(item.lista_compra_id)

        # Eliminar el item
        db.session.delete(item)
        db.session.commit()

        # Volver a renderizar los items de ESA lista
        return cargar_items(lista)

    def cargar_items(lista):
        # ACA ESTABA EL ERROR: usar lista.id, no lista
        items = ItemListaCompra.query.filter_by(lista_compra_id=lista.id).all()
        
        for item in items:
            # Adjuntar el producto para que el template pueda usar item.producto.nombre
            item.producto = Producto.query.get(item.producto_id)

            # Buscar el mejor precio actual para ese producto
            mejor = (
                db.session.query(PrecioProducto.precio, Supermercado.nombre)
                .select_from(ProductoSupermercado)
                .join(
                    PrecioProducto,
                    PrecioProducto.producto_supermercado_id == ProductoSupermercado.id
                )
                .join(
                    Supermercado,
                    Supermercado.id == ProductoSupermercado.supermercado_id
                )
                .filter(ProductoSupermercado.producto_id == item.producto_id)
                .order_by(PrecioProducto.precio.asc())
                .first()
            )

            if mejor:
                item.mejor_precio = type('obj', (object,), {
                    'precio': mejor[0],
                    'supermercado': type('obj', (object,), {'nombre': mejor[1]})
                })
            else:
                item.mejor_precio = None

        # Calcular total estimado de forma segura
        total = 0
        for i in items:
            if getattr(i, 'mejor_precio', None) and i.mejor_precio.precio is not None:
                total += i.mejor_precio.precio * i.cantidad

        return render_template('partials/items_lista.html', items=items, total_estimado=total)

    return app
    
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)