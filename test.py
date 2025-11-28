from app import create_app # o desde donde tengas la instancia de Flask
from utils import normalizar_producto_nombre, registrar_producto_pendiente, revisar_intervenciones
from extensions import db

app = create_app()

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
        'Jabón en Barra Lux 90g'
    ]
    with app.app_context():
        db.create_all()
        revisar_intervenciones()
        for y in x:
            resultado = normalizar_producto_nombre(y)
            if resultado["intervencion"]:
                registrar_producto_pendiente(y, resultado, motivo="marca_no_detectada_o_dudosa")

            print(resultado)