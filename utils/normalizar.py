from revisar_intervenciones import revisar_intervenciones
import re
import unicodedata


def quitar_acentos(s: str) -> str:
    """
    Quita los acentos de un string.
    """
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def limpiar_nombre_producto(nombre: str, unidad_medida: str, marca: str):
    """
    Limpia el nombre del producto utilizando regex:
      - Quita la unidad de medida detectada (solo cuando aparece como palabra o parte de patrón numérico).
      - Quita la marca detectada como palabra completa.
      - Quita caracteres especiales.
      - Normaliza espacios.
      - eliminar acentos y pasar a minúsculas
    """

    nombre_limpio = nombre.lower()
    nombre_limpio = quitar_acentos(nombre_limpio)

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
    """
    Normaliza el nombre del producto, detectando unidad de medida y marca.
    """
    intervencion = False 

    unidad_medida, valor, intervencion_um = detectar_unidad_medida(nombre)
    marca, intervencion_marca = detectar_marca(nombre)

    # Si cualquiera de las dos pide intervención, lo marcamos
    if intervencion_um:
        print("Intervención requerida: unidad de medida no detectada o dudosa.")
        intervencion = "unidad_medida_no_detectada_o_dudosa"
    if intervencion_marca:
        print("Intervención requerida: marca no detectada o dudosa.")
        intervencion = "marca_no_detectada_o_dudosa"

    producto = limpiar_nombre_producto(nombre, valor, marca)

    return {
        "producto": producto,
        "unidad_medida": unidad_medida,
        "valor": valor,
        "marca": marca,
        "intervencion": intervencion
    }

def normalizar(text):
    '''
    Ejecuta la normalización completa de un texto de producto.
    '''
    revisar_intervenciones()
    resultado = normalizar_producto_nombre(text)
    if resultado["intervencion"]:
        registrar_producto_pendiente(text, resultado, motivo=resultado["intervencion"])
        print(f"Producto '{text}' requiere intervención humana.")

    print(f"Normalización completa de '{text}': {resultado}")
    pass