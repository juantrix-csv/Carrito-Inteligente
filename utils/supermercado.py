from models import ListaCompra, ItemListaCompra, Supermercado, ProductoSupermercado, PrecioProducto, Producto

def armar_listado_supermercados(lista_id):
    """
    Dada una lista de compra, arma una estructura con todos los supermercados
    y los items de la lista que tienen en stock, con su precio más barato. 
    """
    lista = ListaCompra.query.get(lista_id)

    if not lista:
        return []

    # Traer los items de esa lista
    items_lista = ItemListaCompra.query.filter_by(lista_compra_id=lista.id).all()

    # Traer TODOS los supermercados
    supermercados = Supermercado.query.all()

    resultado = []

    for superm in supermercados:
        supermercado_dict = {
            "nombre": superm.nombre,
            "items": []
        }

        for item in items_lista:
            # Buscar el producto en ese supermercado
            ps = ProductoSupermercado.query.filter_by(
                supermercado_id=superm.id,
                producto_id=item.producto_id
            ).first()

            if not ps:
                continue

            # Buscar el precio más reciente / más barato
            precio = (
                PrecioProducto.query
                .filter_by(producto_supermercado_id=ps.id)
                .order_by(PrecioProducto.precio.asc())
                .first()
            )

            if precio:
                supermercado_dict["items"].append({
                    "nombre": Producto.query.get(item.producto_id).nombre,
                    "precio": precio.precio * item.cantidad
                })

        resultado.append(supermercado_dict)

    return resultado

def calcular_super_mas_barato(listado_supermercados):
    """
    Recibe una lista donde cada elemento representa un supermercado y contiene:
    {
      "nombre": "Carrefour",
      "items": [
          {"nombre": "pan", "precio": 150.0},
          {"nombre": "huevos", "precio": 350.0}
      ]
    }

    Devuelve el nombre del supermercado con el total más bajo.
    """
    precios_totales = {}

    for supermercado in listado_supermercados:
        nombre_super = supermercado['nombre']
        productos = supermercado.get('items', [])

        total = sum(producto['precio'] for producto in productos)
        precios_totales[nombre_super] = total

    if not precios_totales:
        return None

    return min(precios_totales, key=precios_totales.get)