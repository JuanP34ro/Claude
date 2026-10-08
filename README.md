# Carp Field Notes · versión 0.5

Cuaderno de campo de carpfishing en Orellana (antes «Orellana Atlas»). Los identificadores internos (`orellana-atlas` en el almacenamiento, las copias y la API) se mantienen para conservar los datos guardados.

## Novedades 0.5 · revisión de calidad

- **Abre sin cobertura**: un service worker mínimo (`sw.js`) guarda solo la app (HTML, manifiesto e iconos), con red primero. Nunca guarda mapas, `/api/` ni el tiempo.
- **Avisos visibles** también encima de fichas y pantallas abiertas.
- **Sin toques perdidos** en «Mis cañas» (el reloj y la barra se actualizan sin rehacer los botones), en los puntos del mapa y con la brújula activa (redibujo limitado a cambios de 1° y unas 12 veces por segundo).
- **Importar no borra notas**: al fusionar, el registro de notas de cada spot se une; las fechas futuras de archivos externos se limitan a hoy.
- **Compartir** pregunta si incluir tus notas privadas de los spots.
- **GPX** con identificador y notas propias: reimportar no duplica ni ensucia las notas.
- **Historial** conserva el nombre de la caña y del spot aunque se borren.
- **Tiempo en UTC**: sin desfase con el cambio de hora del 25 de octubre.
- **GPS** no se apaga por un aviso puntual de falta de señal.
- **Modo noche automático** respeta el cambio manual al reabrir la app; restaurar una copia refresca todos los ajustes; la capa batimétrica de una copia pide confirmación.
- **Recebado**: pitido además del aviso, y opción ☀︎ para mantener la pantalla encendida en «Mis cañas».
- **Rendimiento**: puntos del mapa en rojo directo de noche (sin filtros SVG), pulso del spot limitado, teselas fallidas reintentadas, memoria de teselas acotada y liberada al ocultar capas, comprobación del proxy sin bloquear el arranque.
- **iPhone**: sin zoom al escribir (texto de 16 px), respeto de la barra inferior y la muesca, exportaciones por la hoja de Compartir.
- **Seguridad**: el proxy solo devuelve imágenes PNG/JPEG en GetMap y XML en GetCapabilities, con CSP `sandbox`; GetCapabilities ya no admite parámetros de mapa; cabeceras contra el enmarcado (`frame-ancestors`, `X-Frame-Options`); CSV protegido frente a fórmulas.

## Novedades 0.4 · sesión de pesca

- **Ficha del spot**: al tocar un punto del mapa, «Ver» en la lista o «Spot» en una caña, el mapa encuadra el puesto y el spot por encima de una hoja con su resumen (distancia, vueltas, rumbo, fondo, profundidad, alineación, cañas, capturas, cebado total) y un registro de notas con fecha (observación, sondeo, cebado, picada, cambio de montaje) que se mezcla con las capturas y cebados de ese spot. Las notas viajan en las copias y al compartir puntos.
- **Pantalla de cañas** (botón de la caña en el mapa o «Abrir pantalla de cañas» en Sesión): arriba, la vista del puesto dibujada (las cañas en perspectiva hacia el agua sobre el rod pod, con avisadores que se encienden en el agua y parpadean cuando toca recebar, y bajo cada una su reloj, spot y vueltas; al tocarla baja a su tarjeta). Debajo, una tarjeta por caña con cronómetro grande del tiempo en el agua, barra y aviso de recebado, distancia en vueltas y metros, rumbo, montaje, cebo, último cebado, capturas de la sesión, última picada y fondo del spot; botones Lancé, Cebé, PICADA, Recoger y Apuntar.
- **Logo de cuaderno antiguo de cuero** (tapa con textura, pespunte, cantoneras de latón, goma y carpa en pan de oro) en la cabecera y el icono.
- **Tutorial de cuaderno antiguo**: diez páginas (incluye la ficha del spot, «Mis cañas» y cómo instalarla en iPhone y Android) de papel envejecido que pasan con animación de hoja, con dibujos a tinta que se trazan solos y anotaciones manuscritas. Se abre la primera vez y desde Ayuda o Conexión. Respeta «reducir movimiento».
- **Tiempo** (Open-Meteo, CC BY 4.0, sin clave): presión actual y su tendencia en 3, 12 y 24 h, gráfico de 3 días atrás y previsión, aviso de cambio rápido (umbral configurable), viento con rachas y si da de cara, de espalda o lateral respecto al puesto y los spots, tabla de las próximas 24 h. Se envía la zona del puesto redondeada a ~1 km; los últimos datos quedan guardados para verlos sin conexión.
- **Sol y luna** calculados en el móvil (sin conexión): amanecer, anochecer, fase, iluminación y salida y puesta de la luna.
- **Sesión**: cañas (spot, vueltas al clip, montaje, cebo), botones Lancé / Cebé / Picada, temporizador de recebado con aviso (solo con la app abierta) y cebado del día por spot.
- **Diario de capturas**: captura, pez perdido o picada fallida, especie, peso en kg, caña, spot, cebo y montaje. Cada entrada guarda automáticamente presión, tendencia, viento, temperatura, nubosidad y fase lunar de su hora. Resumen de sesión y exportación CSV.
- **Modo nocturno rojo** desde el mapa o Conexión: todo pasa a escala de grises con más contraste y después a rojo puro (sin luz verde ni azul), con intensidad regulable (20–100 %), imágenes del mapa atenuadas para que destaquen puntos y textos,, encendido automático al anochecer y, opcionalmente, un color por mapa (actual rojo, foto histórica ámbar, plano en líneas amarillas) para distinguir la mezcla y la cortina.
- **Modo Orientación** (rosa N del mapa): la aguja señala el norte real y un haz desde tu posición GPS o el puesto muestra hacia dónde apunta el móvil, con marcas cada 50 m en metros y vueltas, y avisa del spot que queda en línea.
- **Cortina plano**: la cortina desliza el plano histórico sobre una mezcla del satélite actual y la foto histórica (la mezcla se ajusta con la opacidad de la fotografía).
- Botón de temperatura actual en el mapa (en lugar de + y −) con la tendencia de la presión; al tocarlo abre la previsión.
- Botón de picada rápida en el mapa e indicadores de viento/presión y de recebado sobre el mapa.


## Novedades 0.3 · carpfishing

- Distancia desde el puesto en metros y en **vueltas de distance sticks** (3,9 m por vuelta por defecto, configurable) y **rumbo** a cada punto, con líneas en el mapa.
- Radios del puesto configurables (hasta cuatro; 200 y 250 m por defecto).
- Tipos de punto: cebado, picadas, enganche/obstáculo, cambio de fondo, cauce antiguo; tipo de fondo y marca de alineación en la orilla.
- GPS continuo y botón **Marcar aquí** con la posición actual.
- **Compartir puntos con compañeros** (GeoJSON por la hoja de Compartir del iPhone). Al importar, los puntos con el mismo identificador se actualizan si son más recientes y no se duplican.
- Recordatorio de copia de seguridad, solicitud de almacenamiento persistente y guardado al pasar la app a segundo plano.
- Menos datos: ortofotos en JPEG cuando el catálogo lo anuncia, imágenes del IGN pedidas directamente (con el proxy como reserva) y caché en la CDN de Vercel para las respuestas del proxy.

- **Apuntar**: guía con la brújula del móvil hacia un punto desde el puesto o desde la posición GPS («Gira 12° a la derecha» / «En línea ✓»). Error típico de la brújula: 5–15°, mayor cerca de metal.
- Estilo clásico (negro, oro envejecido y plata, tipografía grabada y caligráfica del sistema) con medallón e icono propios. No incluye logotipos ni nombres de terceros.

En iPhone, Safari y el icono de la pantalla de inicio guardan los datos por separado: usa siempre el mismo.

Aplicación de investigación cartográfica para Orellana: fotografías aéreas históricas, planos antiguos, puntos, trazados y mediciones propias. Fecha de entrega: 7 de octubre de 2026.

## Novedad: móvil y GitHub/Codex

Para probar desde el iPhone en tu Wi-Fi, ejecuta **`PROBAR_EN_MOVIL_WINDOWS.bat`**
en el PC y abre la dirección de red que muestra. Requiere Python 3.10+ en el PC.
La opción `--lan` es explícita; el lanzador normal continúa limitado al propio ordenador.

Lee **[EMPEZAR.md](EMPEZAR.md)** para la prueba móvil y la publicación.
**[AGENTS.md](AGENTS.md)** y **[SIGUIENTE_PASO_CODEX.md](SIGUIENTE_PASO_CODEX.md)**
preparan la continuidad en Codex. Incluye CI de comprobación, no publicación automática.
No hay repositorio remoto ni despliegue HTTPS creados por esta entrega.

## Estado de esta entrega

La interfaz y la lógica de comparación, anotaciones, medición e intercambio de datos están implementadas. Los servicios oficiales están configurados para consulta en línea.

**La carga real de cartografía de IGN e IDEEX y la cobertura de Orellana NO han podido verificarse desde el entorno de desarrollo.** La red de este entorno está restringida. Las pruebas del navegador emplearon respuestas WMS y almacenamiento simulados; no constituyen una comprobación de mapas reales. El servidor local y la validación de peticiones sí se probaron mediante HTTP local.

**No hay una carta batimétrica de Orellana conectada.** No se incluyen imágenes, profundidades ni puntos inventados. Los vínculos a C-MAP y Garmin no equivalen a una integración.

## Abrir la aplicación

### Vista rápida en un ordenador

Abre `index.html` con tu navegador y conexión a Internet. El archivo incorpora el código y los estilos: no necesita instalar librerías JavaScript. También se entrega por separado como `Orellana_Atlas.html`.

En este modo, las imágenes se solicitan directamente a los proveedores. La lectura de determinados catálogos puede fallar por restricciones de origen del navegador (CORS), por HTTPS o por indisponibilidad de la fuente. No desactives las protecciones del navegador para solucionarlo: utiliza el servidor incluido.

### Proyecto con servidor local

Requiere **Python 3.10 o posterior**, sin paquetes adicionales.

En Windows, extrae toda la carpeta del ZIP y ejecuta `INICIAR_WINDOWS.bat`. En macOS o Linux, ejecuta `INICIAR_MAC_LINUX.command`. También puedes iniciar `python server.py` desde esa carpeta.

El lanzador normal abre el navegador y se limita a `http://127.0.0.1:8765/`. Mantén su ventana abierta mientras uses la aplicación. Para cerrarlo, pulsa Ctrl+C. Si el puerto está ocupado, ejecuta `python server.py --port 8766`.

El servidor solo publica la aplicación, su icono, el manifiesto y dos rutas API. El proxy de mapas se limita a los proveedores oficiales preconfigurados y mantiene la validación HTTPS. No permite indicar una URL arbitraria.

### Uso en iPhone y publicación

El diseño está adaptado a pantalla táctil, pero esta entrega **no está publicada en una dirección web** y no se ha probado en un iPhone físico. Las pruebas móviles se realizaron mediante emulación en Chromium.

Para utilizarla desde fuera de tu Wi-Fi, el paso pendiente es desplegarla en un alojamiento HTTPS. Para una prueba local, utiliza el nuevo lanzador de móvil; por HTTP local no funcionará el GPS del iPhone. El proyecto incluye `vercel.json` y las funciones de `/api` como punto de partida para Vercel. Ese despliegue no está ejecutado ni validado; requiere una cuenta conectada, revisar sus condiciones y probar las fuentes desde ese alojamiento. El HTML descargado no es una URL publicada ni una aplicación iOS instalada.

## Primer uso

En **Capas**, elige el fondo moderno y la fotografía histórica. Activa también el plano para superponer ambos. La opción **Cortina** separa el grupo histórico del mapa moderno; **Mezclar** permite superponerlos usando las transparencias. **Solo actual** oculta el grupo histórico, no una eventual capa batimétrica.

Marca **Puesto** y toca su ubicación. Las circunferencias de 200 y 250 metros son referencias de distancia horizontal, no límites oficiales de un sector de pesca ni metros exactos de hilo desplegado.

En **Puntos**, guarda coordenadas, procedencia, observaciones y, cuando exista una medición, profundidad, fecha y referencia de nivel de agua. **Medir** permite dibujar y guardar un recorrido.

Usa **Guardar copia** antes de cambiar de navegador, dispositivo, dirección web o ubicación del archivo. Una copia JSON conserva el proyecto completo. GeoJSON y GPX permiten intercambiar puntos y trazados; no transfieren mapas ni garantizan compatibilidad con un barco o sonda concreta.

## Cartografía configurada

| Opción | Proveedor / servicio | Resolución técnica de capa |
| --- | --- | --- |
| Ortofoto moderna | IGN / PNOA máxima actualidad | Nombre inicial y comprobación por GetCapabilities |
| Mapa topográfico moderno | IGN cartografía ráster | Nombre inicial y comprobación por GetCapabilities |
| Vuelo 1956–1957 | IGN / PNOA histórico | Nombre inicial y comprobación por GetCapabilities |
| Vuelo 1945–1946 | IDEEX / CICTEX | Identificación del nombre en el catálogo del servidor |
| MTN50 primera edición | IGN | Nombre inicial y comprobación por GetCapabilities |
| Minutas MTN50 | IGN | Identificación del nombre en el catálogo del servidor |
| Badajoz 1960–1967 | IDEEX / CICTEX | Identificación del nombre en el catálogo del servidor |

Los nombres técnicos y las direcciones están en `SOURCES`, al inicio de `app.js`; las direcciones del proxy también están en `wms_proxy.py`. No se elige otra colección si el catálogo no permite identificar la solicitada. Las URLs HTTPS de IDEEX incluidas requieren verificación de disponibilidad; los directorios históricos enlazan también direcciones HTTP.

La fecha de una hoja histórica puede diferir de la de su hoja vecina. La resolución de una imagen no certifica su exactitud posicional. No interpretes las curvas antiguas como profundidades actuales. La aplicación no extrae automáticamente cotas de planos ni genera una batimetría a partir de imágenes.

## Batimetría en línea

La pestaña **Fondo** incluye vínculos a los visores originales y un conector para un WMS autorizado. Para conectarlo se necesitan su URL HTTPS, nombre de capa, versión, crédito y referencia de profundidades. El servicio debe permitir el uso y anunciar imágenes en Web Mercator (EPSG:3857). La casilla de autorización registra tu confirmación; no concede una licencia.

El conector solicita imágenes en línea; no hace falta descargar ni importar cartas. C-MAP Genesis y Navionics no deben tratarse como WMS públicos por defecto. No se incluye ninguna extracción de sus teselas ni se eluden claves, suscripciones o licencias. Navionics necesitaría su integración oficial, una clave y las condiciones de uso correspondientes. La cobertura de Orellana sigue pendiente.

La conexión WMS personalizada se realiza desde el navegador, no a través del proxy oficial. No incluyas credenciales privadas en la URL: las copias JSON conservan la configuración. Registrar profundidades de sonda propias no construye por sí mismo un modelo continuo del fondo.

## Datos, privacidad y limitaciones

Los puntos y las notas se guardan con `localStorage` en el navegador. No hay cuenta, sincronización ni base de datos remota. Borrar los datos del navegador puede borrar el proyecto; exporta copias. En archivos `file://`, el comportamiento de almacenamiento depende del navegador, por lo que se recomienda el servidor local o HTTPS.

Las peticiones WMS transmiten la zona de mapa consultada al proveedor y, en modo servidor, al alojamiento del proxy. No transmiten los textos de los puntos. La ubicación del dispositivo solo se solicita cuando pulsas el botón correspondiente. No se usa analítica.

Las cartas requieren conexión. No hay descarga masiva, paquete de mapas sin conexión ni funcionamiento cartográfico offline garantizado; solo la caché normal del navegador o del servicio. El GPX conserva la profundidad en una extensión propia y en la descripción, **nunca como elevación**; otros programas pueden ignorar las extensiones. Límite de importación: 5 MB y 3.000 elementos; solo puntos y líneas WGS84, no polígonos, cartas comerciales o registros de sonda binarios.

Esta versión es una herramienta de estudio y anotación, no un sistema de navegación, una batimetría certificada ni un sustituto de la observación del terreno y la sonda. Revisa la calidad, la fecha, la referencia y los permisos de cada fuente antes de usarla para decisiones en campo.

## Diagnóstico de fuentes

**Conexión** muestra por separado el estado del catálogo y de las imágenes. “Imágenes recibidas” solo indica que el servidor devolvió imágenes: no confirma que cubran la zona ni que estén correctamente alineadas. Una respuesta transparente puede no contener información útil.

Usa **Reintentar capas activas** o **Releer catálogo**. Si una capa falla, no se sustituye por otra y se mantiene visible la advertencia. **Exportar diagnóstico** permite conservar la URL, nombre de capa, proyección y estado de la conexión para revisar el problema.

## Código y mantenimiento

`app.js`: mapa, WMS, gestos, anotaciones y archivos. `app.css`: diseño. `index.template.html`: estructura. Tras editar estos archivos, ejecuta `python build.py` para reconstruir `index.html`.

`server.py`: servidor local. `wms_proxy.py`: fuentes permitidas y validación. `api/health.py` y `api/wms.py`: adaptadores para despliegue. No hay dependencias de ejecución externas al navegador y a la biblioteca estándar de Python para el modo servidor.

## Fuentes consultadas

- Servicios oficiales del IGN: https://www.ign.es/web/ign/portal/ide-area-nodo-ide-ign
- Directorio IDEEX: https://www.ideex.es/IDEEXVisor/DIRECTORIO_DE_SERVICIOS_Y_CAPAS_DE_LA_IDE_DE_EXTREMADURA.pdf
- Archivo y comparador histórico CICTEX: https://geoportal.ideex.es/pages/memoriaCICTEX
- Ortofotos históricas PNOA: https://pnoa.ign.es/pnoa-imagen/fotogramas-y-ortofotos-historicas
- Metadatos oficiales de minutas MTN50: https://datos.gob.es/es/catalogo/e00125901-spaignminutasmtn50
- C-MAP Genesis: https://www.genesismaps.com/SocialMap
- Integración oficial Garmin/Navionics: https://developer.garmin.com/marine-charts/web/
- Funciones Python de Vercel: https://vercel.com/docs/functions/runtimes/python

La autoría, licencias y condiciones de los mapas pertenecen a sus proveedores. Este proyecto no es una aplicación oficial de IDEEX, IGN, C-MAP, Garmin ni de la organización del WCC.
