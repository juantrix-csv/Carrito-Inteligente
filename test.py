from app import create_app
from extensions import db
from models import Producto
from utils.utils import embed  # asegurate que exista

app = create_app()


def generar_embeddings_productos_faltantes(batch_size: int = 100):
    """
    Recorre todos los productos genéricos que no tengan embedding
    y les genera uno a partir de su nombre.
    """
    productos_sin_embedding = (
        Producto.query
        .filter((Producto.embedding == None) | (Producto.embedding == []))  # type: ignore
        .all()
    )

    total = len(productos_sin_embedding)
    print(f"🔎 Productos genéricos sin embedding: {total}")

    if not productos_sin_embedding:
        print("✅ No hay productos pendientes.")
        return

    procesados = 0

    for prod in productos_sin_embedding:
        texto = (prod.nombre or "").strip()
        if not texto:
            print(f"⚠️ Producto id={prod.id} sin nombre. Se salta.")
            continue

        try:
            emb = embed(texto)
            prod.embedding = emb
            procesados += 1

            if procesados % batch_size == 0:
                db.session.commit()
                print(f"💾 Commit intermedio: {procesados}/{total} productos actualizados...")

        except Exception as e:
            print(f"❌ Error generando embedding para producto id={prod.id}, nombre='{prod.nombre}': {e}")

    db.session.commit()
    print(f"🎉 Listo: {procesados}/{total} productos generaron embedding.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("========== GENERAR EMBEDDINGS PRODUCTOS ==========")
        generar_embeddings_productos_faltantes(batch_size=100)
