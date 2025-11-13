import scrapy
import json


class CarrefourCategoriasSpider(scrapy.Spider):
    name = "carrefour"
    start_urls = [
        "https://www.carrefour.com.ar/api/catalog_system/pub/category/tree/3/"
    ]

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

        for categoria in categorias:
            yield scrapy.Request("https://www.carrefour.com.ar/api/catalog_system/pub/products/search/" + categoria, callback=self.parse_categoria)
        
    def parse_categoria(self, response):
        data = json.loads(response.text)
        productos = self.extraer_productos_categoria(data)
        for p in productos:
            yield p  # Así se envía a la pipeline



            
        
