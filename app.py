from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from extensions import db 
from utils import armar_listado_supermercados, calcular_super_mas_barato
import json 

def create_app():
    
    app = Flask(__name__)

    # Base de datos SQLite en un archivo local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///super_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = "cambia_esta_clave_por_una_muy_larga_y_aleatoria_123456789"
    db.init_app(app)
    from models import Producto, ListaCompra, PrecioProducto, ProductoSupermercado, Supermercado, ItemListaCompra  # ajustá el import según tu estructura

    def obtener_items_y_total(lista):
        # Traer ítems de la lista
        items = ItemListaCompra.query.filter_by(lista_compra_id=lista.id).all()
        
        for item in items:
            # Adjuntar el producto para que el template pueda usar item.producto.nombre
            item.producto = Producto.query.get(item.producto_id)
            # Como todavía no estamos manejando precios, lo dejamos explícito
            item.mejor_precio = None

        # Por ahora no calculamos precios reales
        total = 0

        return items, total

    @app.route('/')
    def home():
        return redirect(url_for('lista_compra_home'))

    @app.route('/lista/')
    def lista_compra_home():
        listas = ListaCompra.query.order_by(ListaCompra.fecha_creacion.desc()).all()
        
        lista_activa = None
        items = []
        total = 0

        if 'lista_activa_id' in session:
            lista_activa = ListaCompra.query.get(session['lista_activa_id'])
            if lista_activa:
                items, total = obtener_items_y_total(lista_activa)

        return render_template(
            'lista_compra.html',
            listas=listas,
            lista_activa=lista_activa,
            items=items,
            total_estimado=total
        )
    
    @app.route('/lista/<int:lista_id>/comparar') # TODO: asegurar de usar comparacion de embeddings
    def comparar_lista(lista_id):
        # Obtenemos la lista
        lista = ListaCompra.query.get_or_404(lista_id)

        # Armamos la estructura con supermercados + items
        listado = armar_listado_supermercados(lista_id)

        # Calculamos el nombre del super más barato
        super_mas_barato = calcular_super_mas_barato(listado)

        # IMPORTANTE: pasar lista al template
        return render_template(
            "comparar.html",
            lista=lista,
            listado=listado,
            super_mas_barato=super_mas_barato
        )

    @app.route('/lista/crear', methods=['POST'])
    def crear_lista():
        nombre = request.form['nombre'].strip()
        if not nombre:
            return "Nombre requerido", 400

        lista = ListaCompra(nombre=nombre)
        db.session.add(lista)
        db.session.commit()

        session['lista_activa_id'] = lista.id

        items, total = obtener_items_y_total(lista)  # va a ser lista vacía

        return render_template(
            'partials/lista_activa.html',
            lista_activa=lista,
            items=items,
            total_estimado=total
        )

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

        # Buscar SOLO productos genéricos
        productos = (
            Producto.query
            .filter(Producto.nombre.ilike(f'%{q}%'))
            .order_by(Producto.nombre.asc())
            .limit(10)
            .all()
        )

        if not productos:
            return '<div class="p-3 text-muted">No se encontraron productos</div>'

        html = '''
        <div class="autocomplete-suggestions shadow-lg bg-white rounded border"
            style="max-height:400px;overflow-y:auto;">
        '''
        
        for prod in productos:
            nombre_js = json.dumps(prod.nombre or "Sin nombre")

            # precio = 0 y "Genérico" son solo placeholders para tu JS actual
            html += f'''
            <div class="px-3 py-3 border-bottom"
                style="cursor:pointer;background:var(--bs-light);"
                onclick='seleccionarProducto({prod.id}, {nombre_js}, 0, "Genérico")'>
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{prod.nombre}</strong><br>
                        <small class="text-muted">Producto genérico</small>
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
        items, total = obtener_items_y_total(lista)
        return render_template(
            'partials/items_lista.html',
            items=items,
            total_estimado=total
        )
    
    @app.route('/lista/<int:lista_id>/eliminar', methods=['POST'])
    def eliminar_lista(lista_id):
        # Buscar la lista
        lista = ListaCompra.query.get_or_404(lista_id)

        # Borrar primero todos los items de esa lista
        ItemListaCompra.query.filter_by(lista_compra_id=lista.id).delete()

        # Borrar la lista
        db.session.delete(lista)
        db.session.commit()

        # Si era la lista activa, sacarla de la sesión
        if session.get('lista_activa_id') == lista.id:
            session.pop('lista_activa_id', None)

        # Volver a la vista principal de listas
        return redirect(url_for('lista_compra_home'))
    
    return app
        
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)