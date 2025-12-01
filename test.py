from app import create_app
from utils import normalizar_producto_nombre, registrar_producto_pendiente, revisar_intervenciones
from extensions import db
from models import Marca  # opcional, para inspección
from pathlib import Path

app = create_app()
RUTA_PENDIENTES = Path("pendientes_revision.csv")

if __name__ == "__main__":
    x = [
        'Desodorante Fig & Suede Dove Men 150ml',
        'Shampoo Sedal 400 ml Reparación Total 5',
        'Leche Entera La Serenísima 1L',
        'Yogurísimo Yogur Bebible Durazno 1.5kg',
        'Queso Cremoso Barra La Paulina x 400g',
        'Arroz Gallo Oro Largo Fino 1kg',
        'Aceite de Girasol Cocinero 900ml',
        'Pan Baguette Bimbo 250g',
        'Jabón en Barra Lux 90g',
        # mas productos de la serenisima:
        'Leche Descremada La Serenísima 1L',
        'Leche Semidescremada La Serenísima 1L',
        'Yogurísimo Yogur Entero Natural 1kg',
        'Yogurísimo Yogur Descremado Natural 1kg',
        'Queso Rallado La Serenísima 100g'
    ]

    with app.app_context():
        db.create_all()

        print("========== 1) Revisar intervenciones anteriores ==========")
        if RUTA_PENDIENTES.exists():
            print(f"[INFO] Archivo {RUTA_PENDIENTES} existe, aplicando revisar_intervenciones()...")
        else:
            print(f"[INFO] Archivo {RUTA_PENDIENTES} NO existe aún.")

        revisar_intervenciones()

        print("\n========== 2) Normalizar productos actuales ==========")
        intervenidos = 0

        for y in x:
            resultado = normalizar_producto_nombre(y)

            print(f"\nProducto original: {y}")
            print(f"  → producto     : {resultado['producto']}")
            print(f"  → unidad_medida: {resultado['unidad_medida']}")
            print(f"  → valor        : {resultado['valor']}")
            print(f"  → marca        : {resultado['marca']}")
            print(f"  → intervencion : {resultado['intervencion']}")

            if resultado["intervencion"]:
                intervenidos += 1
                registrar_producto_pendiente(y, resultado, motivo="marca_no_detectada_o_dudosa")

        print("\n========== RESUMEN ==========")
        print(f"Total productos procesados : {len(x)}")
        print(f"Con intervención requerida : {intervenidos}")

        if RUTA_PENDIENTES.exists():
            print(f"Revisá el CSV: {RUTA_PENDIENTES.resolve()}")
        else:
            print("No se generó pendientes_revision.csv")

        # Opcional: ver cuántas marcas hay en DB
        total_marcas = Marca.query.count()
        print(f"Marcas en la DB: {total_marcas}")
