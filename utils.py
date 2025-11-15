

def calcular_super_mas_barato(listado_supermercados):
    """
    Esta función recibe una lista de diccionarios, donde cada diccionario representa un supermercado
    con su nombre y la lista de productos. La función devuelve el nombre del supermercado
    con el precio más bajo en la suma de los productos.

    :param listado_supermercados: Lista de diccionarios con la estructura:
                                  [{'nombre': 'Supermercado A', 'item': {'nombre': 'pan', 'precio' : 150.0}},
                                   {'nombre': 'Supermercado B', 'item': {'nombre': 'huevos', 'precio' : 350.0}}, ...]
    :return: Nombre del supermercado con el precio más bajo.
    """
    precios_totales = {}

    for supermercado in listado_supermercados:
        nombre_super = supermercado['nombre']
        productos = supermercado.get('items', [])

        total = sum(producto['precio'] for producto in productos)
        precios_totales[nombre_super] = total

    if not precios_totales:
        return None

    super_mas_barato = min(precios_totales, key=precios_totales.get)
    return super_mas_barato
