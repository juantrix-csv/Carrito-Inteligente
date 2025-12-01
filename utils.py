import numpy as np
from models import ListaCompra, ItemListaCompra, Supermercado, ProductoSupermercado, PrecioProducto, Producto, Marca
from sentence_transformers import SentenceTransformer
from unidades_medida import unidades_regex
import re
import unicodedata
from extensions import db
import csv
from pathlib import Path
from datetime import datetime

model = SentenceTransformer('all-MiniLM-L6-v2')
RUTA_PENDIENTES = Path("pendientes_revision.csv")

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



def registrar_producto_pendiente(nombre_original: str, normalizado: dict, motivo: str = ""):
    """
    Guarda en un CSV los productos que requieren intervención humana.
    - nombre_original: string tal como vino del scraper / input
    - normalizado: dict devuelto por normalizar_producto_nombre
    - motivo: texto opcional (ej: 'marca_no_detectada', 'baja_similitud', etc.)
    """
    RUTA_PENDIENTES = Path("pendientes_revision.csv")

    # Definimos las columnas que queremos guardar
    campos = [
        "timestamp",
        "nombre_original",
        "producto",
        "unidad_medida",
        "valor",
        "marca_detectada",
        "intervencion",
        "motivo",
    ]

    # ¿El archivo ya existe?
    existe = RUTA_PENDIENTES.exists()

    with RUTA_PENDIENTES.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)

        # Si el archivo no existía, escribimos encabezado
        if not existe:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "nombre_original": nombre_original,
            "producto": normalizado.get("producto"),
            "unidad_medida": normalizado.get("unidad_medida"),
            "valor": normalizado.get("valor"),
            "marca_detectada": normalizado.get("marca"),
            "intervencion": normalizado.get("intervencion"),
            "motivo": motivo,
        })


def revisar_intervenciones(): # TODO: revisar comportamiento con unidades de medida
    """
    Revisa el CSV de pendientes y:
      - Si se completó 'marca_detectada':
          - Crea la marca si no existe (con embedding + aliases básicos).
          - O, si existe, le agrega sinónimos.
      - Si 'marca_detectada' o la unidad de medida y el valor siguen vacía, mantiene la fila en el CSV
        para revisión futura.
    """
    print("=== INICIANDO revisión de intervenciones ===")

    if not RUTA_PENDIENTES.exists():
        print("[ERROR] No existe pendientes_revision.csv")
        return

    filas_a_revisar = []
    with RUTA_PENDIENTES.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            if not any(fila.values()):
                print("[SKIP] Fila vacía encontrada, ignorando")
                continue
            filas_a_revisar.append(fila)

    if not filas_a_revisar:
        print("[INFO] El CSV está vacío, no hay nada para procesar.")
        return

    print(f"[INFO] {len(filas_a_revisar)} filas cargadas desde el CSV.")

    filas_restantes = []

    for idx, fila in enumerate(filas_a_revisar, start=1):
        print(f"\n--- Procesando fila #{idx} ---")
        print(f"Nombre original: {fila.get('nombre_original')}")
        print(f"Marca detectada (manual): {fila.get('marca_detectada')}")

        marca_detectada = (fila.get("marca_detectada") or "").strip()
        unidad_detectada = (fila.get("unidad_medida") or "").strip()
        valor_detectado = (fila.get("valor") or "").strip()

        # 🔥 Nueva condición: si falta algo → conservar fila
        if not (marca_detectada and unidad_detectada and valor_detectado):
            print("[PENDIENTE] Faltan datos obligatorios (marca / unidad / valor). La fila queda en el CSV.")
            filas_restantes.append(fila)
            continue

        # Si sigue sin completarse → conservar en archivo
        if not marca_detectada:
            nombre_original = fila.get("nombre_original") or ""
            auto_marca, auto_interv = detectar_marca(nombre_original)

            if auto_marca and not auto_interv:
                print(f"[AUTO] Marca '{auto_marca}' detectada automáticamente desde la DB. Fila resuelta.")
                # No la agrego a filas_restantes → desaparece del CSV
                continue
            else:
                print("[PENDIENTE] No se pudo detectar automáticamente, la fila se mantiene en el CSV.")
                filas_restantes.append(fila)
                continue

        marca_canon = marca_detectada.strip()
        marca_norm = normalize_text(marca_canon)
        print(f"[INFO] Marca canonical normalizada: '{marca_norm}'")

        # Buscar si ya existe en DB
        marca_existente = (
            Marca.query
            .filter(db.func.lower(Marca.nombre) == marca_norm)
            .first()
        )

        aliases_nuevos = generar_aliases_basicos(marca_canon)
        print(f"[INFO] Aliases generados: {aliases_nuevos}")

        if not marca_existente:
            print(f"[CREAR] La marca '{marca_canon}' NO existe en la DB. Creando...")

            emb = embed(marca_canon)
            print(f"[EMBED] Tamaño del embedding generado: {len(emb)} valores.")

            nueva_marca = Marca(
                nombre=marca_canon,
                sinonimos=aliases_nuevos,
                embedding=emb
            )
            db.session.add(nueva_marca)
            print(f"[OK] Marca '{marca_canon}' creada con éxito.")
        else:
            print(f"[EXISTE] La marca '{marca_existente.nombre}' ya está en la DB.")
            print("[INFO] Sus aliases actuales son:", marca_existente.sinonimos)

            sinonimos = marca_existente.sinonimos or []
            existentes_norm = {normalize_text(s) for s in sinonimos}
            nombre_canon_norm = normalize_text(marca_existente.nombre)

            agregados = []

            for alias in aliases_nuevos:
                alias_norm = normalize_text(alias)
                if alias_norm not in existentes_norm and alias_norm != nombre_canon_norm:
                    sinonimos.append(alias)
                    agregados.append(alias)

            marca_existente.sinonimos = sinonimos

            if agregados:
                print(f"[UPDATE] Se agregaron nuevos alias: {agregados}")
            else:
                print("[INFO] No había aliases nuevos para agregar.")

        # Fin del procesamiento de la fila
        print("[OK] Fila procesada y no se incluirá nuevamente en el CSV.")
        

    db.session.commit()
    print("\n=== Cambios confirmados en la base de datos ===")

    # Reescribir CSV con las filas que siguen pendientes
    with RUTA_PENDIENTES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=filas_a_revisar[0].keys())
        writer.writeheader()
        for fila in filas_restantes:
            writer.writerow(fila)

    print(f"[INFO] {len(filas_restantes)} filas se mantienen pendientes.")
    print("=== Revisión de intervenciones finalizada ===")


def normalizar(text):
    '''
    Ejecuta la normalización completa de un texto de producto.
    '''
    revisar_intervenciones()
    resultado = normalizar_producto_nombre(text)
    if resultado["intervencion"]:
        registrar_producto_pendiente(text, resultado, motivo="marca_no_detectada_o_dudosa")
        print(f"Producto '{text}' requiere intervención humana.")

    print(f"Normalización completa de '{text}': {resultado}")
    pass

# x = 'Desodorante Fig & Suede Dove Men 150ml'
# print(normalizar_producto_nombre(x))