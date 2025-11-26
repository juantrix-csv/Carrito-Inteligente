import re

unidades_regex = {
    # 1) kg: número + (kg/kilo/kilos/etc)
    "kg": re.compile(
        r"\b\d+([.,]\d+)?\s*(kilos?|kg|kilogram(o|os)?|kgs?|kilograms?)\b",
        re.IGNORECASE
    ),
    
    # 2) gramos: número + (g/gr/grs/gramos/etc)
    "g": re.compile(
        r"\b\d+([.,]\d+)?\s*(gramos?|gramo|gram(me|mes)?|grams?|grs?|gr|gms?|gm)\b",
        re.IGNORECASE
    ),

    # 3) litros: número + (l/lt/lts/litro/etc)
    "litro": re.compile(
        r"\b\d+([.,]\d+)?\s*(litros?|litro|l|lt|lts|liter(s)?|litre(s)?|ltrs?|ltr)\b",
        re.IGNORECASE
    ),

    # 4) mililitros: número + (ml/mililitros/etc)
    "ml": re.compile(
        r"\b\d+([.,]\d+)?\s*(ml|mililitros?|milliliter(s)?|millilitre(s)?)\b",
        re.IGNORECASE
    ),

    # 5) pack / paquete: número opcional + palabra entera
    "pack": re.compile(
        r"\b(pack(s)?|paquete(s)?|package(s)?|pkg(s)?|pkt(s)?)\b",
        re.IGNORECASE
    ),

    # 6) caja
    "caja": re.compile(
        r"\b(caja(s)?|box(es)?|bx(es)?|bx(s)?)\b",
        re.IGNORECASE
    ),

    # 7) barra
    "barra": re.compile(
        r"\b(barra(s)?|bar(s)?|br(s)?)\b",
        re.IGNORECASE
    ),

    # 8) sobre
    "sobre": re.compile(
        r"\b(sobre(s)?|envelope(s)?|env(s)?)\b",
        re.IGNORECASE
    ),

    # 9) unidad: ojo con "u" sola → solo la aceptamos si hay número
    "unidad": re.compile(
        r"\b\d+\s*(unidad(es)?|u\.?|unit(s)?|piece(s)?|pc(s)?)\b",
        re.IGNORECASE
    ),
}