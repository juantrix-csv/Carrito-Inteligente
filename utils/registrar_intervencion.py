import csv
from pathlib import Path
from datetime import datetime

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