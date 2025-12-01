from ..unidades_medida import unidades_regex

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
        
    return None, None, True