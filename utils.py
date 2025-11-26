import numpy as np
from models import *
from sentence_transformers import SentenceTransformer
from unidades_medida import unidades_regex
import re 

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed(text: str) -> np.ndarray:
    vec = model.encode([text])[0].astype("float32")
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

def armar_listado_supermercados(lista_id):
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

def detectar_unidad_medida(nombre: str):
    """
    Detecta la unidad de medida en el nombre del producto usando regex con contexto.
    Retorna (unidad_canonica, requiere_intervencion_humana).
    """
    nombre_lower = nombre.lower()

    for unidad_canonica, pattern in unidades_regex.items():
        match = pattern.search(nombre_lower)
        if match:
            valor = match.group(0)
            return unidad_canonica, valor, False
        
    return None, None, False

def detectar_marca(nombre):
    nombre_lower = nombre.lower()
    marcas = Marca.query.all()

    # 1) búsqueda exacta por marca
    for marca in marcas:
        marca_lower = marca.nombre.lower()
        pattern = rf"\b{re.escape(marca_lower)}\b"
        if re.search(pattern, nombre_lower):
            return marca.nombre, False

    # 2) sinónimos
    for marca in marcas:
        if marca.sinonimos:
            for sinonimo in marca.sinonimos:
                sinonimo_lower = sinonimo.lower()
                pattern = rf"\b{re.escape(sinonimo_lower)}\b"
                if re.search(pattern, nombre_lower):
                    return marca.nombre, False

    # 3) embeddings
    nombre_embedding = embed(nombre_lower)

    mejor_marca = None
    mejor_similitud = 0.0
    umbral_similitud = 0.8

    for marca in marcas:
        if marca.embedding:
            marca_embedding = np.array(marca.embedding, dtype="float32")
            # si los guardaste ya normalizados, esto es coseno
            similitud = float(np.dot(nombre_embedding, marca_embedding))
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_marca = marca.nombre

    if mejor_similitud >= umbral_similitud:
        return mejor_marca, False

    return None, True


def limpiar_nombre_producto(nombre: str, unidad_medida: str, marca: str):
    """
    Limpia el nombre del producto utilizando regex:
      - Quita la unidad de medida detectada (solo cuando aparece como palabra o parte de patrón numérico).
      - Quita la marca detectada como palabra completa.
      - Quita caracteres especiales.
      - Normaliza espacios.
    """

    nombre_limpio = nombre.lower()

    # 1) Eliminar marca (como palabra completa o casi completa)
    if marca:
        marca_norm = re.escape(marca.lower())
        # match como palabra: “ coca cola ”, " coca ", "coca-cola" etc.
        pattern_marca = rf"\b{marca_norm}\b"
        nombre_limpio = re.sub(pattern_marca, " ", nombre_limpio)


    # 2) Eliminar unidad de medida
    # (ej: “500 g”, “1.5 kg”, “900 ml”, “1 l”)
    if unidad_medida:
        unidad_norm = re.escape(unidad_medida.lower())
        
        # patrón: número + unidad (ej: 500 g) o unidad sola como palabra
        pattern_unidad = rf"\b\d+([.,]\d+)?\s*{unidad_norm}\b|\b{unidad_norm}\b"
        nombre_limpio = re.sub(pattern_unidad, " ", nombre_limpio)

    # 3) Quitar caracteres no alfanuméricos excepto espacio
    nombre_limpio = re.sub(r"[^a-z0-9\s]", " ", nombre_limpio)


    # 4) Remover múltiples espacios
    nombre_limpio = re.sub(r"\s+", " ", nombre_limpio)

    return nombre_limpio.strip()


def normalizar_producto_nombre(nombre):
    intervencion = False 

    unidad_medida, valor, intervencion_um = detectar_unidad_medida(nombre)
    marca, intervencion_marca = detectar_marca(nombre)

    # Si cualquiera de las dos pide intervención, lo marcamos
    intervencion = intervencion_um or intervencion_marca

    producto = limpiar_nombre_producto(nombre, unidad_medida, marca)

    return {
        "producto": producto,
        "unidad_medida": unidad_medida,
        "valor": valor,
        "marca": marca,
        "intervencion": intervencion
    }

x = 'Desodorante Fig & Suede Dove Men 150ml'
print(normalizar_producto_nombre(x))