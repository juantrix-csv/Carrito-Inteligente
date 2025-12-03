import numpy as np
from models import Producto
from . import model

def embed(text: str):
    """
    Genera un embedding normalizado para el texto dado.
    Retorna una lista de floats.
    """
    vec = model.encode([text])[0].astype("float32")
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def cosine_similarity(vec1, vec2):
    """
    Calcula la similitud coseno entre dos vectores.
    Ambos vectores deben ser listas de floats de la misma longitud.
    Retorna un float entre -1 y 1.
    """
    if len(vec1) != len(vec2):
        raise ValueError("Los vectores deben tener la misma longitud.")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)

def encontrar_producto_por_nombre_semantico(nombre, marca):
    """
    Busca un producto en la base de datos cuyo nombre sea semánticamente similar al dado.
    Filtrando por los productos de la misma marca.
    Retorna el primer producto encontrado o None si no hay coincidencias.
    """
    embedding_nombre = embed(nombre)
    productos = Producto.query.filter_by(marca=marca).all()

    mejor_producto = None
    mejor_similitud = -1.0

    for producto in productos:
        if producto.embedding:
            similitud = cosine_similarity(embedding_nombre, producto.embedding)
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_producto = producto

    return mejor_producto, mejor_similitud
    