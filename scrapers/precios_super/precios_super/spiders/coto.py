import scrapy
import json

class CotoSpider(scrapy.Spider):
    name = "coto"

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,   # MUY IMPORTANTE
    }

    def start_requests(self):
        # 1) Entrar a la home para obtener cookies válidas
        url_home = "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio"
        yield scrapy.Request(url_home, callback=self.parse_home)

    def parse_home(self, response):
        self.logger.info(f"Entramos al home. Cookies iniciales: {response.headers.getlist('Set-Cookie')}")

        # 2) Ahora pedimos la API de categorías CON ESTA SESIÓN
        url_categorias = (
            "https://www.cotodigital.com.ar/sitios/cdigi/categoria/catalogo-almac%C3%A9n/_/N-8pub5z?format=json"
        )
        yield scrapy.Request(url_categorias, callback=self.parse_categorias)

    def parse_categorias(self, response):
        self.logger.info("CATEGORÍAS OBTENIDAS CORRECTAMENTE")

        data = json.loads(response.text)

        # Extraemos categorías recursivamente
        categorias = []
        def recorrer(n):
            if isinstance(n, dict):
                if (
                    "categoryId" in n and
                    "displayName" in n and
                    "navigationState" in n
                ):
                    nav = n["navigationState"]
                    categorias.append({
                        "nombre": n["displayName"],
                        "nav": nav,
                        "url_json": f"https://www.cotodigital.com.ar/sitios/cdigi/{nav}?format=json"
                    })
                for v in n.values():
                    recorrer(v)
            elif isinstance(n, list):
                for elem in n:
                    recorrer(elem)

        recorrer(data)

        self.logger.info(f"Categorías encontradas: {len(categorias)}")

        # 3) Ahora scrapeamos UNA categoría de prueba
        #    Para debug, mandamos solo la primera. Después lo hacemos con todas.
        cat = categorias[0]
        self.logger.info(f"Probando categoría: {cat['nombre']}")

        yield scrapy.Request(
            cat["url_json"],
            callback=self.parse_categoria,
            meta={"categoria": cat["nombre"], "nav": cat["nav"]}
        )

    def parse_categorias(self, response):
        self.logger.info(f"STATUS getCategorias: {response.status}")
        self.logger.info(f"Content-Type: {response.headers.get('Content-Type')}")

        texto = response.text.strip()
        if not texto:
            self.logger.error("getCategorias devolvió cuerpo vacío")
            return

        # Logueamos un pedazo para ver si es HTML o JSON
        self.logger.info("Primeros 400 chars de getCategorias:")
        self.logger.info(texto[:400])

        try:
            data = json.loads(texto)
        except json.JSONDecodeError as e:
            self.logger.error(f"No es JSON válido: {e}")
            # Acá salimos para no romper el spider
            return

        # Si llega acá, data ES JSON y recién ahí seguimos
        self.logger.info("JSON de categorías decodificado OK")
        

        categoria = response.meta["categoria"]
        self.logger.info(f"Scrapeando categoría: {categoria}")

        try:
            data = json.loads(response.text)
        except Exception:
            self.logger.error("La respuesta NO es JSON. Probablemente faltan cookies o headers.")
            self.logger.error(response.text[:400])
            return

        # EJEMPLO: en Coto suele venir como "results" o "products"
        productos_brutos = []

        if "results" in data:
            productos_brutos = data["results"]
        elif "productos" in data:
            productos_brutos = data["productos"]
        else:
            self.logger.warning("No pude encontrar lista de productos en el JSON")
            self.logger.warning(response.text[:400])
            return

        for prod in productos_brutos:
            yield {
                "categoria": categoria,
                "nombre": prod.get("descripcion") or prod.get("displayName"),
                "precio": prod.get("precio") or prod.get("PrecioLista"),
                "marca": prod.get("marca"),
                "id_producto": prod.get("id"),
                "ean": prod.get("ean"),
                "url": prod.get("url"),
            }
