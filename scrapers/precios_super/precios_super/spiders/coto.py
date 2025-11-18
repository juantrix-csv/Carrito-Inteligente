import scrapy
import json
import re
import math
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from coto_parser import extract_products_from_root

class CotoSpider(scrapy.Spider):
    name = "coto"

    custom_settings = {
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,   # MUY IMPORTANTE
    }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _first(value, default=None):
        """Devuelve el primer elemento si es lista, o el valor tal cual."""
        if isinstance(value, list):
            return value[0] if value else default
        return value if value is not None else default

    @staticmethod
    def _extract_number(s):
        """
        Extrae un número razonable de un string.

        Maneja:
        - "$19.199,20"    -> 19199.2
        - "$19199.20"     -> 19199.2
        - "Precio Regular: $23999" -> 23999.0
        - "23999.000000"  -> 23999.0
        """
        if not s:
            return None

        s = str(s)

        # primer bloque "numérico" que encontremos
        m = re.search(r"[0-9][0-9.,]*", s)
        if not m:
            return None

        num_str = m.group(0)

        # caso con punto y coma -> estilo "19.199,20"
        if "." in num_str and "," in num_str:
            num_str = num_str.replace(".", "").replace(",", ".")
        # solo coma -> "23999,50"
        elif "," in num_str:
            num_str = num_str.replace(",", ".")
        # solo punto -> "23999.000000" -> lo dejamos así

        try:
            return float(num_str)
        except ValueError:
            return None

    def _parse_precio_from_attributes(self, attrs):
        """
        Intenta sacar el mejor precio posible usando los campos
        que Coto manda en el JSON.

        Prioridad:
        1) sku.activePrice
        2) sku.dtoPrice (precioLista / precio)
        3) product.dtoDescuentos* (precioDescuento / precioRegular / textoPrecioRegular)
        4) sku.referencePrice
        5) product.PrecioLista / product.precioLista
        """

        # 1) sku.activePrice
        val = self._first(attrs.get("sku.activePrice"))
        if val:
            if isinstance(val, (int, float)):
                return float(val)
            num = self._extract_number(val)
            if num is not None:
                return num

        # 2) dtoPrice (JSON con precioLista, precio, etc.)
        raw = self._first(attrs.get("sku.dtoPrice"))
        if raw:
            try:
                obj = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(obj, dict):
                    # 👇 acá priorizamos precioLista; si querés al revés poné ["precio", "precioLista"]
                    for k in ["precioLista", "precio"]:
                        if k in obj and obj[k] is not None:
                            val = obj[k]
                            if isinstance(val, (int, float)):
                                return float(val)
                            num = self._extract_number(val)
                            if num is not None:
                                return num
            except Exception:
                pass

        # 3) Promos: dtoDescuentos
        dto_keys = [
            "product.dtoDescuentos",
            "product.dtoDescuentosMediosPago",
            "product.dtoDescuentosTarjeta",
            "dtoDescuentos",
            "dtoDescuentosMediosPago",
            "dtoDescuentosTarjeta",
        ]

        for key in dto_keys:
            raw = self._first(attrs.get(key))
            if not raw or raw == "[]":
                continue

            try:
                arr = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue

            if not isinstance(arr, list) or not arr:
                continue

            desc = arr[0]

            # 3.a precioDescuento (ej: "$4605.00c/u")
            val = desc.get("precioDescuento")
            if val:
                num = self._extract_number(val)
                if num is not None:
                    return num

            # 3.b precioRegular
            val = desc.get("precioRegular")
            if val:
                num = self._extract_number(val)
                if num is not None:
                    return num

            # 3.c textoPrecioRegular (ej: "Precio Contado: $9210")
            val = desc.get("textoPrecioRegular")
            if val:
                num = self._extract_number(val)
                if num is not None:
                    return num

        # 4) sku.referencePrice
        val = self._first(attrs.get("sku.referencePrice"))
        if val:
            if isinstance(val, (int, float)):
                return float(val)
            num = self._extract_number(val)
            if num is not None:
                return num

        # 5) Fallback: product.PrecioLista / product.precioLista
        for key in ["product.PrecioLista", "product.precioLista"]:
            val = self._first(attrs.get(key))
            if val:
                if isinstance(val, (int, float)):
                    return float(val)
                num = self._extract_number(val)
                if num is not None:
                    return num

        return None



    # ---------- Helpers NUEVOS para paginado ---------- #

    @staticmethod
    def _find_results_list(node):
        """
        Busca el nodo con "@type": "Category_ResultsList"
        que tiene recsPerPage y totalNumRecs.
        """
        if isinstance(node, dict):
            if node.get("@type") == "Category_ResultsList" and "totalNumRecs" in node:
                return node
            for v in node.values():
                res = CotoSpider._find_results_list(v)
                if res is not None:
                    return res
        elif isinstance(node, list):
            for item in node:
                res = CotoSpider._find_results_list(item)
                if res is not None:
                    return res
        return None

    @staticmethod
    def _build_url_with_offset(first_page_url: str, offset: int, recs_per_page: int) -> str:
        """
        A partir de la URL de la primera página, genera una URL con:
          - No = offset
          - Nrpp = recs_per_page
        Mantiene Nf, Nr, format, etc.
        """
        parsed = urlparse(first_page_url)
        qs = parse_qs(parsed.query)

        qs["No"] = [str(offset)]
        qs["Nrpp"] = [str(recs_per_page)]

        new_query = urlencode(qs, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)

    # ------------------------------------------------------------------ #
    # Flow
    # ------------------------------------------------------------------ #

    def start_requests(self):
        # 1) Entrar a la home para obtener cookies válidas
        url_home = "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio"
        yield scrapy.Request(url_home, callback=self.parse_home)

    def parse_home(self, response):
        self.logger.info(
            f"Entramos al home. Cookies iniciales: "
            f"{response.headers.getlist('Set-Cookie')}"
        )

        # 2) Ahora pedimos la API de categorías CON ESTA SESIÓN
        url_categorias = (
            "https://www.cotodigital.com.ar/"
            "sitios/cdigi/categoria/catalogo-almac%C3%A9n/_/N-8pub5z?format=json"
        )
        yield scrapy.Request(
            url_categorias,
            callback=self.parse_categorias_root,
        )

    # ------------ PRIMERA PASADA: obtener lista de categorías ------------

    def parse_categorias_root(self, response):
        self.logger.info("CATEGORÍAS OBTENIDAS CORRECTAMENTE")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"No es JSON válido en categorías root: {e}")
            self.logger.error(response.text[:400])
            return

        categorias = []

        def recorrer(n):
            if isinstance(n, dict):
                if (
                    "categoryId" in n
                    and "displayName" in n
                    and "navigationState" in n
                ):
                    nav = n["navigationState"]

                    base = "https://www.cotodigital.com.ar/sitios/cdigi/"
                    # nav generalmente ya trae query (?Nf=...&No=0&Nrpp=24...)
                    if "?" in nav:
                        url_json = f"{base}{nav}&format=json"
                    else:
                        url_json = f"{base}{nav}?format=json"

                    categorias.append({
                        "nombre": n["displayName"],
                        "nav": nav,
                        "url_json": url_json,
                    })
                for v in n.values():
                    recorrer(v)
            elif isinstance(n, list):
                for elem in n:
                    recorrer(elem)

        recorrer(data)

        self.logger.info(f"Categorías encontradas: {len(categorias)}")
        if not categorias:
            self.logger.warning("No se encontró ninguna categoría en el JSON")
            return

        for cat in categorias:
            self.logger.info(f"Agendando categoría: {cat['nombre']}")
            yield scrapy.Request(
                cat["url_json"],
                callback=self.parse_categoria,
                meta={
                    "categoria": cat["nombre"],
                    "nav": cat["nav"],
                    "first_page_url": cat["url_json"],
                    "page_idx": 0,  # primera página
                },
            )

    # ------------ SEGUNDA PASADA: productos de una categoría ------------

    def parse_categoria(self, response):
        self.logger.info("---------------------------------------------------------------------------")
        self.logger.info(f"STATUS categoría: {response.status}")
        self.logger.info(f"Content-Type: {response.headers.get('Content-Type')}")

        texto = response.text.strip()
        if not texto:
            self.logger.error("La categoría devolvió cuerpo vacío")
            return

        try:
            data = json.loads(texto)
        except json.JSONDecodeError as e:
            self.logger.error(f"No es JSON válido en categoría: {e}")
            self.logger.error(texto[:400])
            return

        categoria = response.meta.get("categoria", "desconocida")
        first_page_url = response.meta.get("first_page_url", response.url)
        page_idx = response.meta.get("page_idx", 0)

        # ---------- PAGINADO: solo lo calculamos en la primera página ---------- #
        if page_idx == 0:
            results_list = self._find_results_list(data)
            if results_list:
                try:
                    recs_per_page = int(results_list.get("recsPerPage", 0) or 0)
                    total = int(results_list.get("totalNumRecs", 0) or 0)
                except ValueError:
                    recs_per_page = 0
                    total = 0

                if recs_per_page and total:
                    num_pages = math.ceil(total / recs_per_page)
                    self.logger.info(
                        f"[{categoria}] recsPerPage={recs_per_page}, "
                        f"total={total}, páginas={num_pages}"
                    )

                    # Arrancamos en 1 porque la página 0 ya se está procesando
                    for next_page_idx in range(1, num_pages):
                        offset = next_page_idx * recs_per_page
                        page_url = self._build_url_with_offset(
                            first_page_url, offset, recs_per_page
                        )
                        self.logger.info(
                            f"[{categoria}] Agendando página "
                            f"{next_page_idx+1}/{num_pages} -> {page_url}"
                        )
                        yield scrapy.Request(
                            page_url,
                            callback=self.parse_categoria,
                            meta={
                                "categoria": categoria,
                                "nav": response.meta.get("nav"),
                                "first_page_url": first_page_url,
                                "page_idx": next_page_idx,
                            },
                        )
                else:
                    self.logger.warning(
                        f"[{categoria}] No se pudieron obtener recsPerPage/totalNumRecs"
                    )
            else:
                self.logger.warning(
                    f"[{categoria}] No se encontró Category_ResultsList en el JSON"
                )

        # ---------- EXTRACCIÓN DE PRODUCTOS DE ESTA PÁGINA ---------- #

        # Usamos el parser externo que ya probaste en tu script
        productos = extract_products_from_root(data)

        self.logger.info(
            f"[{categoria}] (página {page_idx}) productos encontrados: {len(productos)}"
        )

        for p in productos:
            # Si querés que la categoría sea la que pasás por meta (por si difiere
            # de parentCategory / allAncestors del JSON):
            p["categoria"] = categoria

            # Campos extra del supermercado para tu modelo
            p["supermercado_nombre"] = "Coto"
            p["supermercado_url"] = "https://www.cotodigital.com.ar"
            p["supermercado_ciudad"] = "CABA"

            yield p

