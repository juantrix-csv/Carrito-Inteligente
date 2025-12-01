import scrapy
import json


class CarrefourCategoriasSpider(scrapy.Spider): # TODO: revisar porque no recorre todos los productos de la pagina
    name = "carrefour"
    start_urls = [
        "https://www.carrefour.com.ar/api/catalog_system/pub/category/tree/3/"
    ]
    custom_settings = {
        "LOG_LEVEL": "INFO",
    }
    
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.total_productos = 0

    def extraer_productos_categoria(self, data):
        """
        data: resultado de json.loads(...) de la API de categoría de Carrefour.
        Devuelve una lista de diccionarios con la info principal de cada producto.
        """
        productos = []

        for prod in data:
            product_id = prod.get("productId")
            nombre = prod.get("productName")
            marca = prod.get("brand")
            categorias_path = prod.get("categories", [])  # lista de strings tipo "/Lácteos/Huevos/"
            url_producto = prod.get("link")

            # Categoria "principal": tomo el primer path y me quedo con el último segmento
            categoria = None
            if categorias_path:
                # ej: "/Lácteos y productos frescos/Huevos/"
                path = categorias_path[0].strip("/")         # "Lácteos y productos frescos/Huevos"
                partes = path.split("/")                     # ["Lácteos y productos frescos", "Huevos"]
                categoria = partes[-1] if partes else None

            # Datos que vienen en items[0]
            items = prod.get("items") or []
            item = items[0] if items else {}

            ean = item.get("ean")
            unidad = item.get("measurementUnit")          # ej: "un"
            multiplicador = item.get("unitMultiplier")    # ej: 1

            # Imagen principal (si existe)
            imagen_url = None
            images = item.get("images") or []
            if images:
                imagen_url = images[0].get("imageUrl")

            # Precio desde sellers[0].commertialOffer.Price
            precio = None
            sellers = item.get("sellers") or []
            if sellers:
                commertial = sellers[0].get("commertialOffer") or {}
                precio = commertial.get("Price")  # normalmente viene en centavos

            producto_info = {
                "product_id": product_id,
                "nombre": nombre,
                "marca": marca,
                "categoria": categoria,
                "categorias_path": categorias_path,
                "precio": precio,
                "unidad": unidad,
                "multiplicador": multiplicador,
                "ean": ean,
                "url": url_producto,
                "imagen": imagen_url,
                "supermercado_nombre": "Carrefour",
                "supermercado_url": "https://www.carrefour.com.ar/",
                "supermercado_ciudad": ""
            }
            productos.append(producto_info)

        return productos

    def parse(self, response):
        data = json.loads(response.text)

        categorias = []

        def recorrer_nodo(nodo):
            nombre = nodo.get("name")
            if nombre:
                categorias.append(nombre.replace(" ", "-"))

            # hijos (subcategorías)
            for child in nodo.get("children", []):
                recorrer_nodo(child)

        for nodo in data:
            recorrer_nodo(nodo)

        self.logger.info(f"Encontradas {len(categorias)} categorías")

        for categoria in categorias:
            url = (
                f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search/"
                f"{categoria}?_from=0&_to=49"
            )
            yield scrapy.Request(
                url,
                callback=self.parse_categoria,
                meta={"categoria_slug": categoria, "desde": 0, "hasta": 49}
            )
        
    def parse_categoria(self, response):
        categoria_slug = response.meta["categoria_slug"]
        desde = response.meta["desde"]
        hasta = response.meta["hasta"]

        data = json.loads(response.text)
        self.logger.info(f"[{categoria_slug}] {len(data)} productos en rango {desde}-{hasta}")
        productos = self.extraer_productos_categoria(data)
        self.total_productos += len(productos)

        for p in productos:
            yield p

        # Si devolvió productos, intento pedir la siguiente "página"
        if data:
            siguiente_desde = hasta + 1
            siguiente_hasta = hasta + 50  # mismo tamaño de ventana
            next_url = (
                f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search/"
                f"{categoria_slug}?_from={siguiente_desde}&_to={siguiente_hasta}"
            )

            self.logger.info(f"[{categoria_slug}] siguiente página {siguiente_desde}-{siguiente_hasta}")
            yield scrapy.Request(
                next_url,
                callback=self.parse_categoria,
                meta={
                    "categoria_slug": categoria_slug,
                    "desde": siguiente_desde,
                    "hasta": siguiente_hasta,
                }
            )

        self.logger.info(
            f"[{categoria_slug}] acumulado total_productos = {self.total_productos}"
        )


            
        
