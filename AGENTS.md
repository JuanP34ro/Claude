# Orellana Atlas — instrucciones del proyecto

## Objetivo y estado
Aplicación web en español para investigar Orellana con fotografía histórica, planos,
puntos propios y mediciones. Mantener buena experiencia táctil en Safari/iPhone.
La cartografía real aún necesita validación en Orellana. La batimetría no está integrada.
No afirmar que una capa, un despliegue o una prueba física funcionan sin verificarlos.

## Arquitectura
Sin framework, npm ni dependencias JavaScript de producción.
Editar `app.js`, `app.css` e `index.template.html`; `index.html` es un artefacto generado.
`server.py`: biblioteca estándar Python 3.10+, solo loopback por defecto; `--lan` es opt-in.
`wms_proxy.py`: proxy HTTPS restringido a fuentes IGN/IDEEX predefinidas.
`api/`: adaptadores de Vercel. No exponer el servidor local de desarrollo a Internet.
`sw.js`: service worker para abrir la app sin conexión (HTML, manifiesto, iconos) y servir los mapas que el usuario descarga a propósito en «Mapas sin conexión» (caché `cfn-tiles-*`, solo capas IGN/IDEEX con licencia CC BY 4.0 y su atribución). No cachear por su cuenta mapas, `/api/` ni Open-Meteo.

## Comandos
- Reconstruir: `python build.py`.
- Comprobar sincronización: `python build.py --check`.
- Sintaxis JS: `node --check app.js`.
- Pruebas sin red externa: `python -m unittest discover -s tests -v`.
- Vista local: `python server.py --no-browser` (puerto 8765).
- Wi-Fi de confianza, solo a petición del usuario: `python server.py --lan`.

## Reglas de trabajo
1. Reconstruir y ejecutar las comprobaciones antes de entregar cambios.
2. Conservar `orellana-atlas-v1` y el esquema de los datos guardados; migrar si se cambia.
3. No inventar batimetría, sectores, puntos de pesca ni cobertura de los mapas.
4. No extraer teselas privadas de C-MAP/Navionics, omitir atribuciones ni eludir licencias.
5. No cambiar un fallo de red por un éxito simulado. Los mocks pertenecen solo a pruebas.
6. No desactivar HTTPS/CORS, ampliar el proxy a URLs arbitrarias ni añadir claves al cliente.
7. No subir puntos reales, exportaciones de pesca, diagnósticos, tokens o `.env` a GitHub.
8. No publicar, hacer público el repositorio, activar servicios de pago o abrir puertos sin permiso.
9. Guardar copias antes de cambiar dominio: localStorage no sincroniza dispositivos/orígenes.
10. No reescribir el proyecto con otro framework sin una razón aprobada por el usuario.

## Próximas tareas
Leer `SIGUIENTE_PASO_CODEX.md`. Priorizar validar IGN/IDEEX y despliegue HTTPS,
no añadir datos ficticios. Distinguir pruebas locales, emulación y pruebas en iPhone físico.
