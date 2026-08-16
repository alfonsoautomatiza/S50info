# Notas para la certificación (Notes for certification)

Texto recomendado para el campo "Notes for certification" de Partner Center:

> S50Info es una herramienta de consola (CLI) para consultar y exportar datos de SAGE 50.
>
> Requisito: SAGE 50 instalado en el equipo. En equipos sin SAGE 50, la primera ejecución abre un asistente de configuración inicial que busca el terminal de SAGE 50 automáticamente, permite indicarlo manualmente u ofrece descargarlo (http://descargas.sage.es/sage50/sage50.zip). Sin SAGE 50, la herramienta termina con un mensaje claro y sin errores.
>
> La configuración se guarda en `%APPDATA%\s50info\config.ini` y las exportaciones se crean en la carpeta `resultados` del directorio de lanzamiento.
>
> Comandos: `s50info info` (comprueba conexión), `s50info sql "select * from #clientes"` (consultas de lectura), `s50info export "select * from #clientes"` (exportación), `s50info run script` (automatización).