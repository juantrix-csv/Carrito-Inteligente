# Carrito-Inteligente
Una app donde podes cargar tu lista de la compra mensual y ver en que supermercado tu compra es mas barata.

## Descripción

Carrito-Inteligente permite crear y administrar tu lista de la compra mensual y comparar precios entre supermercados para identificar dónde te conviene comprar. Diseño pensado para facilitar la carga de productos, comparar totales y generar reportes simples.

## Características

- Crear, editar y eliminar ítems de la lista de la compra.
- Comparación de precios entre supermercados.
- Cálculo automático del costo total por tienda.
- Filtros por categoría y búsqueda rápida.
- Exportar/guardar listas (CSV/JSON).

## Tecnologías

Indica aquí las tecnologías usadas (ej. Node.js, React, Python, SQLite, Docker). Ejemplo:
- Frontend: React / Vue / Svelte
- Backend: Node.js (Express) / Flask / Django
- Base de datos: SQLite / PostgreSQL

## Instalación

1. Clona el repositorio:
    git clone <URL-del-repositorio>
    cd <directorio-del-proyecto>

2. Instala dependencias (ejemplos):
    - Node.js:
      npm install
      npm run dev
    - Python:
      pip install -r requirements.txt
      flask run

3. Configura variables de entorno:
    - Crear un archivo .env con las claves necesarias (p. ej. DATABASE_URL, API_KEYS).

4. (Opcional) Ejecutar con Docker:
    docker compose up --build

Ajusta los comandos según la stack real del proyecto.

## Uso

- Accede a la interfaz web en http://localhost:3000 (o el puerto configurado).
- Crea una nueva lista y añade productos con su precio y supermercado.
- Usa la función de comparación para ver el coste por tienda.
- Exporta tu lista si necesitas un respaldo.

## Contribuir

1. Crea una rama con tu feature/bugfix:
    git checkout -b feature/mi-mejora
2. Realiza cambios y commitea:
    git commit -m "Descripción breve"
3. Abre un Pull Request describiendo el cambio y pruebas realizadas.

Lee CONTRIBUTING.md (si existe) para normas de desarrollo y estilo.

## Tests

Describe cómo ejecutar tests si los hay. Ejemplo:
- npm test
- pytest tests/

## Licencia

Proyecto bajo licencia MIT. Sustituye por la licencia que corresponda.

## Contacto

Reportes de bugs, dudas o sugerencias mediante Issues en el repositorio o por correo a tu-email@ejemplo.com.
