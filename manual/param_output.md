# Parámetro: --output

El parámetro `--output` (o alias `-o`) define el nombre base del archivo de salida que se generará.

## Sintaxis

```bash
s50info --sql2doc "SQL" --output "nombre_archivo"
s50info -d "SQL" -o "nombre_archivo"
```

## Detalles Técnicos

*   **Tipo**: String.
*   **Requerido**: No (Si se omite, se suele generar un nombre por defecto basado en timestamp o tabla).
*   **Nota Importante**: No incluya la extensión del archivo. La extensión se añade automáticamente según el `--formato` seleccionado (ej. .xlsx, .json).

## Ejemplos de Uso

### Definir nombre específico
```bash
s50info -d "SELECT * FROM CLIENTES" -f xlsx -o "Reporte_Clientes_2024"
```
*(Generará el archivo `Reporte_Clientes_2024.xlsx`)*

## Relacionado con:
*   [--sql2doc](param_sqltodic.md): Comando principal de exportación.
*   [--formato](param_formato.md): Define la extensión que se añadirá.
*   [Volver al Índice](index.md)
