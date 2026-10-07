# Siguiente paso: validar y publicar, sin rehacer el proyecto

## Qué pide el propietario
Probar Orellana Atlas desde su iPhone y continuar el desarrollo con Codex sobre GitHub.
La configuración del repositorio y del alojamiento está preparada, pero NO hay un
repositorio remoto creado ni una dirección HTTPS de esta entrega confirmada.

## Orden de trabajo
1. Leer `AGENTS.md`, `README.md` y `EMPEZAR.md`. Ejecutar las comprobaciones existentes.
2. Antes de crear el repositorio, confirmar cuenta/destino y privacidad con el propietario.
   Nombre sugerido: `orellana-atlas`. No asumir autorización para hacerlo público.
3. Subir el contenido de esta carpeta a la raíz del repositorio, no el ZIP como único archivo.
   Revisar `git status` y no incluir exportaciones con puntos, diagnósticos o credenciales.
4. Revisar la integración Vercel conservada. La app requiere `/api/health` y `/api/wms`
   para activar el proxy; probar la ruta final sin `.py` en el despliegue.
   No publicar un repositorio privado entero como recursos estáticos.
5. Desplegar únicamente cuando exista autorización y acceso al alojamiento.
   El repositorio privado no equivale a una aplicación web privada. Confirmar el acceso del sitio.
6. Probar GetCapabilities y GetMap reales en IGN/IDEEX sobre Orellana. Anotar URL,
   capa, CRS, tiempo de respuesta y cobertura útil. Distinguir error HTTP, CORS, TLS,
   capa inexistente, imagen transparente y falta de cobertura. No sustituir fuentes a escondidas.
7. Probar la URL HTTPS en Safari/iPhone: arrastre, zoom de dos dedos, cortina, panel,
   formulario de punto, radios, exportación/importación, cierre y reapertura, y GPS con permiso.
8. Solo después revisar una integración batimétrica autorizada. Los enlaces comerciales
   existentes NO son capas ni prueban cobertura de Orellana.

## Comprobaciones
`python build.py --check`
`node --check app.js`
`python -m unittest discover -s tests -v`

## Qué debe devolver Codex
Cambios realizados, pruebas realmente ejecutadas, URL del repositorio si se creó,
URL funcional de la app si se publicó y limitaciones pendientes. No presentar una URL
estimada como existente. No se necesitan claves OpenAI para ejecutar este atlas.
