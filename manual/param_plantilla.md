# Parámetro: --plantilla

El parámetro `--plantilla` (o alias `-t`) permite especificar la ruta a un archivo de plantilla personalizado cuando se exportan datos en formato `txt`.

## Sintaxis

```bash
s50info --sql2doc "SQL" --formato txt --plantilla "ruta/a/plantilla.txt"
s50info -d "SQL" -f txt -t "ruta/a/plantilla.txt"
```

## Detalles Técnicos

*   **Tipo**: String (Ruta de archivo válida).
*   **Requerido**: No.
*   **Uso**:
    *   S50Info inyectará los datos obtenidos de la consulta SQL en la plantilla proporcionada.
    *   Este mecanismo es útil para generar reportes con encabezados, pies de página o formatos específicos de texto fijo.

## Ejemplos de Uso

### Exportar usando una plantilla
```bash
s50info -d "SELECT * FROM PEDIDOS" -f txt -t "./templates/pedidos.txt" -o reporte_pedidos
```

## Relacionado con:
*   [--sql2doc](param_sqltodic.md): Comando de exportación.
*   [--formato](param_formato.md): Debe ser `txt` para que la plantilla surta efecto.
*   [Volver al Índice](index.md)
