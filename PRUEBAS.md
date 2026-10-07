# Pruebas de Orellana Atlas 0.1

Fecha: 7 de octubre de 2026.

## Alcance

La navegación y la red externa del entorno de desarrollo están restringidas. Para las pruebas de interfaz se insertó la aplicación en Chromium mediante Playwright y se sustituyeron, únicamente dentro del banco de pruebas, las respuestas WMS y el almacenamiento del navegador por dobles de prueba. Las imágenes de prueba indicaban expresamente que NO eran cartografía real. Ningún doble, punto o imagen de prueba está incluido en la aplicación entregada.

La prueba de exportación comprobó el contenido de los archivos generados; el guardado físico mediante el diálogo de descargas del navegador no se verificó. La prueba de persistencia comprobó la serialización y recuperación del estado desde el almacenamiento simulado; no verifica la política de almacenamiento de Safari ni de cada modalidad de archivo local.

## Interfaz y lógica: 29 comprobaciones superadas

- Inicio de escritorio sin errores JS
- Respuesta WMS simulada detectada
- Capas predeterminadas correctas
- Peticiones WMS Mercator con BBOX y 512 px
- Foto y plano histórico simultáneos
- Descubrimiento de minutas desde catálogo simulado
- Descubrimiento IDEEX 1945 desde catálogo simulado
- Transparencia independiente
- Puesto y radios geodésicos guardados
- Anillos 200/250 m representados
- Profundidad, fuente y referencia guardadas
- Nombre HTML tratado como texto
- Medición y guardado de trazado
- GeoJSON exportado con tres elementos
- GPX conserva profundidades sin inventar altitud
- Serialización y restauración de estado (almacenamiento simulado)
- Importación GeoJSON
- Conversión WGS84-Mercator reversible
- Distancias de 200 y 250 m coherentes
- Búsqueda por coordenadas WGS84
- Zoom operativo
- Batimetría no fabricada
- Sin errores JS tras las acciones
- Móvil sin desbordamiento horizontal
- Panel móvil abre
- Creación táctil de puesto
- Móvil sin errores JavaScript
- Fallos de red comunicados, sin mapa falso
- Fallos de red no rompen interfaz

## Servidor: 14 pruebas superadas

Diez pruebas unitarias de validación de URL y parámetros: petición válida, catálogo, lista de fuentes, rechazo de URL arbitraria, duplicados, operaciones no permitidas, extensión invertida, NaN, dimensiones y proyección no admitida.

Cuatro pruebas reales por HTTP contra el servidor local: respuesta de salud, entrega de la aplicación, bloqueo del acceso a archivos de código y rechazo de una fuente no autorizada. Estas pruebas no necesitaron acceder a Internet.

También se verificó la sintaxis JavaScript con `node --check` y la compilación Python de los módulos. Se revisaron capturas de escritorio (1440 × 1000) y móvil emulado (390 × 844), incluida la visualización del error de conexión.

## Pendiente de verificación real

La disponibilidad de IGN/IDEEX, HTTPS, cabeceras CORS, identificación de capas en sus catálogos reales, cobertura y alineación de las imágenes en Orellana. El contenido exacto de cada hoja y año. La integración con una fuente batimétrica autorizada. El despliegue Vercel/HTTPS. El uso en Safari/iPhone físico, permisos GPS y persistencia de sus datos. La compatibilidad de GPX con el equipo concreto del usuario.

No se ha probado ni se promete navegación, funcionamiento sin conexión, generación de batimetría o cartografía comercial integrada.
