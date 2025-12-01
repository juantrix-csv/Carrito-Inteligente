from unicodedata import unicodedata

def normalize_text(s: str) -> str:
    """
    Normaliza un string para comparaciones:
    - pasa a minúsculas
    - quita acentos
    - normaliza espacios
    """
    s = s.lower().strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())

def generar_aliases_basicos(nombre_marca: str):
    """
    A partir de 'La Serenísima' genera variantes útiles:
    - 'La Serenísima' (tal cual)
    - versión normalizada sin acentos: 'la serenisima'
    - sin artículo ('la', 'el', 'los', 'las'): 'serenisima'
    """
    aliases = set()

    original = nombre_marca.strip()
    aliases.add(original)

    norm = normalize_text(original)          # la serenisima
    aliases.add(norm)

    palabras = norm.split()
    if palabras and palabras[0] in {"la", "el", "los", "las"} and len(palabras) > 1:
        # serenisima
        aliases.add(" ".join(palabras[1:]))

    return list(aliases)