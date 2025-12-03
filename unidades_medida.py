import re

unidades_regex = {
    # 1 kg, 1kg, 1.5 kg, 1,5kg, etc.
    "kg": re.compile(
        r"\b(\d+(?:[.,]\d+)?)\s*(kilos?|kg|kgs?|kilogramos?)\b",
        re.IGNORECASE
    ),

    # 250 g, 250g, 0.5 g, etc.
    "g": re.compile(
        r"\b(\d+(?:[.,]\d+)?)\s*(gramos?|g|grs?|gr|grams?)\b",
        re.IGNORECASE
    ),

    # 900 ml, 900ml, 1.5 ml...
    "ml": re.compile(
        r"\b(\d+(?:[.,]\d+)?)\s*(mililitros?|ml|milliliters?)\b",
        re.IGNORECASE
    ),

    # 1 l, 1l, 1 lt, 1lts, 1 litro, etc.
    "litro": re.compile(
        r"\b(\d+(?:[.,]\d+)?)\s*(l|lt|lts|litros?)\b",
        re.IGNORECASE
    ),

    # opcionales, por si los usás
    "unidad": re.compile(
        r"\b(\d+)\s*(u\.?|unidades?|unit[s]?)\b",
        re.IGNORECASE
    )
}
