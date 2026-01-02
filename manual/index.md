# Manual Técnico de S50Info

Bienvenido al manual técnico de **S50Info**, la herramienta de línea de comandos para la administración y consulta de bases de datos Sage50.

Este manual detalla cada uno de los parámetros disponibles en la aplicación, con ejemplos de uso y descripciones técnicas.

## Índice de Parámetros

### Consultas y Exportación
*   [--sql (Ejecución SQL)](param_sql.md): Ejecuta consultas SQL directas y muestra resultados en consola.
*   [--sql2doc (Exportación SQL)](param_sqltodic.md): Exporta resultados de consultas SQL a diversos formatos (Excel, JSON, etc.).

### Opciones de Exportación
*   [--formato](param_formato.md): Define el formato del archivo de salida (txt, xlsx, json, csv, html).
*   [--output](param_output.md): Especifica el nombre base del archivo de salida.
*   [--plantilla](param_plantilla.md): Define una plantilla personalizada para la exportación en texto.
*   [--comprimir](param_comprimir.md): Comprime los resultados generados en un archivo ZIP.

### Ejecución de Scripts
*   [--exe (Ejecutar Script)](param_exe.md): Ejecuta scripts de Python externos con contexto de S50Info.

### Utilidades
*   [--clave](param_clave.md): Obtiene la contraseña de la base de datos SQL de Sage50.
*   [--noupdate](param_noupdate.md): Evita la comprobación automática de actualizaciones.
*   [--reset](param_reset.md): Opciones para reiniciar logs o estados.

---
*Generado automáticamente por S50Info DocGenerator*
