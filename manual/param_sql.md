# Parámetro: --sql

El parámetro `--sql` (o su alias `-s`) permite ejecutar una consulta SQL directa contra la base de datos de Sage50 conectada y mostrar los resultados directamente en la salida estándar (consola).

## Sintaxis

```bash
s50info --sql "CONSULTA_SQL"
s50info -s "CONSULTA_SQL"
```

## Detalles Técnicos

*   **Tipo**: String (Consulta SQL válida).
*   **Requerido**: No (Opcional).
*   **Comportamiento**:
    *   Establece conexión con la base de datos Sage50.
    *   Ejecuta la sentencia SQL proporcionada.
    *   Si la consulta devuelve filas (ej. `SELECT`), las muestra formateadas en la consola.
    *   Es útil para verificaciones rápidas de datos sin necesidad de generar archivos.

## Ejemplos de Uso

### Consulta Simple
Obtener los 5 primeros clientes:
```bash
s50info --sql "SELECT TOP 5 CODIGO, NOMBRE FROM CLIENTES"
```

### Consulta con Filtro
Buscar artículos con stock negativo:
```bash
s50info -s "SELECT CODIGO, NOMBRE, STOCK FROM ARTICULOS WHERE STOCK < 0"
```

## Relacionado con:
*   [--sql2doc](param_sqltodic.md): Si necesita guardar los resultados en un archivo en lugar de verlos en pantalla.
*   [--noupdate](param_noupdate.md): Para ejecutar consultas rápidas saltando la comprobación de actualizaciones.
*   [Volver al Índice](index.md)
