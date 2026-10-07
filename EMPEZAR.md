# Probar en iPhone y continuar con Codex

## Probar hoy desde casa, sin publicar
Necesitas el PC con Python 3.10+ y el iPhone conectados a la misma red local de confianza.

1. Extrae el ZIP completo en el PC.
2. Ejecuta `PROBAR_EN_MOVIL_WINDOWS.bat` y acepta el modo de red local.
3. La ventana muestra las direcciones de red del PC. Abre en Safari la correspondiente
   a la Wi-Fi de casa. No copies la dirección 127.0.0.1: esa solo sirve en el propio PC.
4. Deja el PC encendido y la ventana abierta. Para terminar, pulsa Ctrl+C en el PC.

El PC puede estar conectado por cable al mismo router; el teléfono, por Wi-Fi.
Si Windows pregunta, permite Python solo en redes privadas. No desactives el firewall
completo ni abras puertos en el router. Una red de invitados, una VPN o el aislamiento
de dispositivos pueden impedir la conexión. Esta vista previa local no tiene contraseña.

Los gestos y puntos pueden probarse; las imágenes dependen de los servicios externos.
El GPS del iPhone necesita HTTPS y no está disponible con la dirección HTTP de esta prueba.
Los puntos se guardan en el navegador del dispositivo que los crea, no se sincronizan al PC.

## Uso desde cualquier sitio: GitHub + alojamiento HTTPS
GitHub guarda el código. Para abrir la app en Safari hace falta además un despliegue web.
La ruta propuesta es repositorio privado personal + Vercel, que permite las funciones
Python del proxy. La configuración está incluida, pero no ejecutada.

- Nombre sugerido para el repositorio: `orellana-atlas`.
- Subir el contenido extraído como archivos del repositorio; subir solo el ZIP no basta.
- Conectar el repositorio a Vercel, revisar permisos y configuración, y validar el resultado.
- El proyecto usa `index.html` generado y versionado. Reconstruir con `python build.py`
  antes de enviar cambios. No hace falta instalar dependencias de la aplicación.
- GitHub Pages solo alojaría la versión estática/directa: no ejecuta este proxy Python.
  No elegirlo como equivalente a la versión completa sin validar los catálogos directos.
- El código puede ser privado mientras la web es pública. Revisar por separado el acceso
  a los dos servicios; no incluir en el código puntos, claves ni información personal.

Una vez exista la URL HTTPS, abrirla en Safari y usar Compartir > Añadir a pantalla de inicio
> Abrir como app web (si aparece) > Añadir. Este acceso no descarga las cartas ni añade modo offline.
Antes de cambiar de dirección o dispositivo, usar Guardar copia e importar en el destino.

## Continuar con Codex
En Codex web, configurar un entorno con acceso al repositorio GitHub. Autorizar solo
el repositorio necesario y comprobar permisos de escritura cuando se vayan a subir cambios.
En VS Code, abrir la carpeta extraída o clonar el repositorio y usar la extensión Codex.
`AGENTS.md` contiene el contexto permanente y `SIGUIENTE_PASO_CODEX.md` el trabajo pendiente.
Conectar GitHub para lectura en ChatGPT no garantiza permisos de escritura.

## Estado de la entrega
Preparado localmente: proyecto para GitHub, AGENTS.md, comprobaciones y vista previa LAN.
Pendiente: conexión a cuentas, creación/push del repositorio, despliegue HTTPS,
cartografía real completa sobre Orellana y prueba en iPhone físico. No hay batimetría conectada.

## Documentación oficial (consultada el 7 de octubre de 2026)
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://vercel.com/docs/git/vercel-for-github
- https://vercel.com/docs/functions/runtimes/python
- https://developers.openai.com/codex/cloud
- https://developers.openai.com/codex/guides/agents-md
- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://support.apple.com/es-es/guide/iphone/iphea86e5236/ios
- https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API
