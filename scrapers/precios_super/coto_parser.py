# coto_parser.py
import json
import re


def first_value(attrs: dict, key: str, default=None):
    """
    Los atributos de Coto vienen como:
    "product.displayName": ["Nombre del producto"]
    Esta función te devuelve el primer valor de esa lista.
    """
    if key not in attrs:
        return default
    value = attrs[key]
    if isinstance(value, list):
        return value[0] if value else default
    return value or default


def extract_number(s):
    """
    Extrae un número flotante razonable de un string.

    Ejemplos:
    - "$19.199,20"    -> 19199.2
    - "$19199.20"     -> 19199.2
    - "Precio Contado: $23999" -> 23999.0
    - "23999.000000"  -> 23999.0
    - "$4605.00c/u"   -> 4605.0
    """
    if s is None:
        return None

    s = str(s)

    m = re.search(r"[0-9][0-9.,]*", s)
    if not m:
        return None

    num_str = m.group(0)

    # caso "19.199,20"
    if "." in num_str and "," in num_str:
        num_str = num_str.replace(".", "").replace(",", ".")
    # caso "23999,50"
    elif "," in num_str:
        num_str = num_str.replace(",", ".")
    # caso "23999.000000" → se deja así

    try:
        return float(num_str)
    except ValueError:
        return None


def compute_price(attrs: dict):
    """
    Calcula el precio "actual" del producto usando varias fuentes.

    Prioridad:
    1) Promos: product.dtoDescuentos* (precioDescuento > precioRegular > textoPrecioRegular)
    2) sku.activePrice
    3) sku.dtoPrice (precio > precioLista)
    4) sku.referencePrice
    """

    # 1) Promos: dtoDescuentos y variantes
    dto_keys = [
        "product.dtoDescuentos",
        "product.dtoDescuentosMediosPago",
        "product.dtoDescuentosTarjeta",
        "dtoDescuentos",
        "dtoDescuentosMediosPago",
        "dtoDescuentosTarjeta",
    ]

    for key in dto_keys:
        raw = first_value(attrs, key)
        if not raw or raw == "[]":
            continue

        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue

        if not isinstance(arr, list) or not arr:
            continue

        desc = arr[0]

        # 1.a precioDescuento: ej "$4605.00c/u" (precio unitario promo 2x1, 3x2, etc.)
        val = desc.get("precioDescuento")
        if val:
            num = extract_number(val)
            if num is not None:
                return num

        # 1.b precioRegular (a veces lo usan también)
        val = desc.get("precioRegular")
        if val:
            num = extract_number(val)
            if num is not None:
                return num

        # 1.c textoPrecioRegular: "Precio Contado: $9210"
        val = desc.get("textoPrecioRegular")
        if val:
            num = extract_number(val)
            if num is not None:
                return num

    # 2) sku.activePrice (precio principal “normal”)
    val = first_value(attrs, "sku.activePrice")
    if val is not None:
        # a veces viene como float directo, a veces como string
        if isinstance(val, (int, float)):
            return float(val)
        num = extract_number(val)
        if num is not None:
            return num

    # 3) sku.dtoPrice: JSON con {precioLista, precio, ...}
    raw = first_value(attrs, "sku.dtoPrice")
    if raw:
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(obj, dict):
                # Preferimos "precio" sobre "precioLista" (lista suele ser precio de lista)
                for field in ["precio", "precioLista"]:
                    val = obj.get(field)
                    if val is None:
                        continue
                    if isinstance(val, (int, float)):
                        return float(val)
                    num = extract_number(val)
                    if num is not None:
                        return num
        except Exception:
            pass

    # 4) sku.referencePrice como fallback
    val = first_value(attrs, "sku.referencePrice")
    if val is not None:
        if isinstance(val, (int, float)):
            return float(val)
        num = extract_number(val)
        if num is not None:
            return num

    # Si no encontramos nada, devolvemos None
    return None


def extract_products_from_root(root):
    """
    Recorre el JSON completo buscando nodos con 'attributes'
    que tengan info de producto (displayName + MARCA/brand, etc).
    Devuelve una lista de dicts simplificados.
    """
    products = []

    def _walk(node):
        # Si es dict, miro si tiene 'attributes'
        if isinstance(node, dict):
            attrs = node.get("attributes")

            # Heurística: es un producto completo si tiene displayName y marca
            if isinstance(attrs, dict) and "product.displayName" in attrs and (
                "product.MARCA" in attrs or "product.brand" in attrs
            ):
                # nombre
                nombre = first_value(attrs, "product.displayName", "")

                # marca (puede venir como product.MARCA o product.brand)
                marca = first_value(attrs, "product.MARCA") or first_value(
                    attrs, "product.brand"
                )

                # product_id
                product_id = first_value(attrs, "product.repositoryId")

                # ean
                ean = first_value(attrs, "product.eanPrincipal")

                # categoría: primero intento con parentCategory.displayName,
                # si no, uso el último de allAncestors.displayName.
                categoria = first_value(attrs, "parentCategory.displayName")
                if categoria is None:
                    anc = attrs.get("allAncestors.displayName")
                    if isinstance(anc, list) and anc:
                        categoria = anc[-1]

                # precio: calculado con la lógica de arriba
                precio = compute_price(attrs)

                # url interna: priorizo product.url, luego sku.url, luego baseUrl
                url_interna = (
                    first_value(attrs, "product.url")
                    or first_value(attrs, "sku.url")
                    or first_value(attrs, "product.baseUrl")
                )

                products.append(
                    {
                        "categoria": categoria,
                        "nombre": nombre,
                        "precio": precio,
                        "marca": marca,
                        "product_id": product_id,
                        "ean": ean,
                        "url": url_interna,
                    }
                )

            # Sigo recorriendo el resto de las claves
            for v in node.values():
                _walk(v)

        # Si es lista, recorro cada elemento
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(root)
    return products
