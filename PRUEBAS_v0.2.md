# Validación de la preparación móvil / GitHub — 7 de octubre de 2026

## Ejecutado en esta entrega
- `python build.py --check`: correcto; index.html coincide con fuentes.
- `node --check app.js`: correcto.
- Compilación Python de servidor, proxy y adaptadores: correcta.
- `python -m unittest discover -s tests -v`: 14 pruebas correctas.
  Cubren HTML generado, iconos/manifiesto, exclusiones de archivos personales,
  catálogo de ficheros publicados, bloqueo de lectura de fuentes/archivos privados,
  health, HEAD, parámetros WMS, redirecciones y detección de IP privada.
- Arranque real `server.py --lan --no-browser` y consulta HTTP local a health: correctos.
  La prueba confirma el arranque y el indicador LAN, no la conexión de un iPhone físico.

## No verificado
- El navegador administrado del entorno bloqueó la navegación tanto a la URL local
  como al archivo local (`ERR_BLOCKED_BY_ADMINISTRATOR`). No se modificaron esas
  restricciones. El test opcional `tests/smoke_browser.py` queda para ejecutar en un
  entorno que permita la vista previa; no se presenta como prueba superada de la 0.2.
- Safari/iPhone real, Windows real y paso de tráfico entre dos dispositivos en una Wi-Fi.
- Respuestas y cobertura útil actuales de los mapas IGN/IDEEX sobre Orellana.
- Publicación GitHub/Vercel, permisos de cuentas y dirección HTTPS.
- Batimetría: sigue sin estar conectada.

Las pruebas automáticas no consultan proveedores cartográficos. No se han añadido
mapas, curvas, profundidades ni puntos ficticios a los archivos de la aplicación.
`PRUEBAS.md` conserva el informe de la entrega 0.1, no una nueva ejecución de esas pruebas.
