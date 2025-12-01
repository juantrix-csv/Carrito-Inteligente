from . import embed, RUTA_PENDIENTES
import csv
from detectar_marca import detectar_marca
from normalizar import normalize_text
from generar_alias import generar_aliases_basicos
from models import Marca
from extensions import db


def revisar_intervenciones(): # TODO: revisar comportamiento con unidades de medida
    """
    Revisa el CSV de pendientes y:
      - Si se completó 'marca_detectada':
          - Crea la marca si no existe (con embedding + aliases básicos).
          - O, si existe, le agrega sinónimos.
      - Si 'marca_detectada' o la unidad de medida y el valor siguen vacía, mantiene la fila en el CSV
        para revisión futura.
    """
    print("=== INICIANDO revisión de intervenciones ===")

    if not RUTA_PENDIENTES.exists():
        print("[ERROR] No existe pendientes_revision.csv")
        return

    filas_a_revisar = []
    with RUTA_PENDIENTES.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            if not any(fila.values()):
                print("[SKIP] Fila vacía encontrada, ignorando")
                continue
            filas_a_revisar.append(fila)

    if not filas_a_revisar:
        print("[INFO] El CSV está vacío, no hay nada para procesar.")
        return

    print(f"[INFO] {len(filas_a_revisar)} filas cargadas desde el CSV.")

    filas_restantes = []

    for idx, fila in enumerate(filas_a_revisar, start=1):
        print(f"\n--- Procesando fila #{idx} ---")
        print(f"Nombre original: {fila.get('nombre_original')}")
        print(f"Marca detectada (manual): {fila.get('marca_detectada')}")

        marca_detectada = (fila.get("marca_detectada") or "").strip()
        unidad_detectada = (fila.get("unidad_medida") or "").strip()
        valor_detectado = (fila.get("valor") or "").strip()

        # 🔥 Nueva condición: si falta algo → conservar fila
        if not (marca_detectada and unidad_detectada and valor_detectado):
            print("[PENDIENTE] Faltan datos obligatorios (marca / unidad / valor). La fila queda en el CSV.")
            filas_restantes.append(fila)
            continue

        # Si sigue sin completarse → conservar en archivo
        if not marca_detectada:
            nombre_original = fila.get("nombre_original") or ""
            auto_marca, auto_interv = detectar_marca(nombre_original)

            if auto_marca and not auto_interv:
                print(f"[AUTO] Marca '{auto_marca}' detectada automáticamente desde la DB. Fila resuelta.")
                # No la agrego a filas_restantes → desaparece del CSV
                continue
            else:
                print("[PENDIENTE] No se pudo detectar automáticamente, la fila se mantiene en el CSV.")
                filas_restantes.append(fila)
                continue

        marca_canon = marca_detectada.strip()
        marca_norm = normalize_text(marca_canon)
        print(f"[INFO] Marca canonical normalizada: '{marca_norm}'")

        # Buscar si ya existe en DB
        marca_existente = (
            Marca.query
            .filter(db.func.lower(Marca.nombre) == marca_norm)
            .first()
        )

        aliases_nuevos = generar_aliases_basicos(marca_canon)
        print(f"[INFO] Aliases generados: {aliases_nuevos}")

        if not marca_existente:
            print(f"[CREAR] La marca '{marca_canon}' NO existe en la DB. Creando...")

            emb = embed(marca_canon)
            print(f"[EMBED] Tamaño del embedding generado: {len(emb)} valores.")

            nueva_marca = Marca(
                nombre=marca_canon,
                sinonimos=aliases_nuevos,
                embedding=emb
            )
            db.session.add(nueva_marca)
            print(f"[OK] Marca '{marca_canon}' creada con éxito.")
        else:
            print(f"[EXISTE] La marca '{marca_existente.nombre}' ya está en la DB.")
            print("[INFO] Sus aliases actuales son:", marca_existente.sinonimos)

            sinonimos = marca_existente.sinonimos or []
            existentes_norm = {normalize_text(s) for s in sinonimos}
            nombre_canon_norm = normalize_text(marca_existente.nombre)

            agregados = []

            for alias in aliases_nuevos:
                alias_norm = normalize_text(alias)
                if alias_norm not in existentes_norm and alias_norm != nombre_canon_norm:
                    sinonimos.append(alias)
                    agregados.append(alias)

            marca_existente.sinonimos = sinonimos

            if agregados:
                print(f"[UPDATE] Se agregaron nuevos alias: {agregados}")
            else:
                print("[INFO] No había aliases nuevos para agregar.")

        # Fin del procesamiento de la fila
        print("[OK] Fila procesada y no se incluirá nuevamente en el CSV.")
        

    db.session.commit()
    print("\n=== Cambios confirmados en la base de datos ===")

    # Reescribir CSV con las filas que siguen pendientes
    with RUTA_PENDIENTES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=filas_a_revisar[0].keys())
        writer.writeheader()
        for fila in filas_restantes:
            writer.writerow(fila)

    print(f"[INFO] {len(filas_restantes)} filas se mantienen pendientes.")
    print("=== Revisión de intervenciones finalizada ===")