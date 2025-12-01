from embedding import embed
from models import Marca
from normalizar import quitar_acentos
import re
import numpy as np

def detectar_marca(nombre):
    """
    Detecta la marca en el nombre del producto.
    """
    nombre_lower = quitar_acentos(nombre).lower()
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