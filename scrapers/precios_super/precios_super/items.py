# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductoItem(scrapy.Item):
    nombre = scrapy.Field()
    precio = scrapy.Field()
    marca = scrapy.Field()
    url = scrapy.Field()
    supermercado = scrapy.Field()
    codigo_externo = scrapy.Field()
