# Parámetro: --exe (Ejecutar Script)

El parámetro `--exe` (o alias `-e`) permite ejecutar scripts de Python externos utilizando el entorno y contexto de conexión de S50Info.

## Sintaxis

```bash
s50info --exe "ruta/al/script.py"
s50info --exe "ruta/a/carpeta/"
```

## Detalles Técnicos

*   **Tipo**: String (Ruta de archivo .py o directorio).
*   **Requerido**: No.
*   **Funcionalidad**:
    *   **Archivo .py**: Carga y ejecuta el script Python especificado.
    *   **Directorio**: Busca y ejecuta secuencialmente todos los archivos `.py` dentro de esa carpeta.
    *   **Contexto**: Inyecta objetos globales en el script ejecutado (como `proceso`) para que pueda interactuar con la API de Sage50 sin necesidad de reinicializar la conexión.

## Ejemplos de Uso

### Ejecutar un script de mantenimiento personalizado
```bash
s50info --exe "./scripts/limpieza_tarifas.py"
```

### Ejecutar un lote de scripts de actualización
```bash
s50info --exe "./actualizaciones_v2/"
```

## Relacionado con:
*   [Volver al Índice](index.md)
