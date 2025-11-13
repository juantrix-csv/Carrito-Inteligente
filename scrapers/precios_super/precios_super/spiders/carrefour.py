import scrapy
import json

class CarrefourCategoriasSpider(scrapy.Spider):
    name = "carrefour"
    start_urls = [
        "https://www.carrefour.com.ar/api/catalog_system/pub/category/tree/3/"
    ]

    def parse(self, response):
        data = json.loads(response.text)

        categorias = []
        urls = []

        def recorrer_nodo(nodo):
            nombre = nodo.get("name")
            url = nodo.get("url")
            if nombre:
                categorias.append(nombre)
            if url:
                urls.append(response.urljoin(url))

            # hijos (subcategorías)
            for child in nodo.get("children", []):
                recorrer_nodo(child)

        for nodo in data:
            recorrer_nodo(nodo)

        yield {
            "categorias": categorias,
            "urls": urls
        }

