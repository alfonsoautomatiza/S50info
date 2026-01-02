# Parámetro: --sql2doc (o --sqltodic)

El parámetro `--sql2doc` (alias `-d` o internamente `sqltodic`) es la función principal de exportación de S50Info. Permite ejecutar una consulta SQL y guardar el resultado en un archivo con un formato específico.

## Sintaxis

```bash
s50info --sql2doc "CONSULTA_SQL" [OPCIONES]
s50info -d "CONSULTA_SQL" [OPCIONES]
```

## Detalles Técnicos

*   **Tipo**: String (Consulta SQL válida).
*   **Requerido**: No (Opcional).
*   **Comportamiento**:
    *   Ejecuta la consulta SQL.
    *   Procesa los resultados para exportarlos.
    *   Utiliza los parámetros complementarios (`--formato`, `--output`, `--plantilla`, `--comprimir`) para determinar cómo guardar los datos.

## Parámetros Relacionados (Opcionales)

Para controlar la salida de este comando, se utilizan:
*   [--formato](param_formato.md): Define si es Excel, CSV, JSON, etc.
*   [--output](param_output.md): Nombre del archivo resultante.
*   [--plantilla](param_plantilla.md): Plantilla para formato TXT.
*   [--comprimir](param_comprimir.md): Crear ZIP.

## Ejemplos de Uso

### Exportación Básica a Texto (Default)
```bash
s50info -d "SELECT * FROM CLIENTES" -o listado_clientes
```
*(Genera un archivo `listado_clientes.txt`)*

### Exportación a Excel
```bash
s50info --sql2doc "SELECT * FROM ARTICULOS" --formato xlsx --output catalogo
```
*(Genera `catalogo.xlsx`)*

### Exportación JSON Comprimida
```bash
s50info -d "SELECT CODIGO, NOMBRE FROM PROVEEDORES" -f json -o proveedores -z
```
*(Genera `proveedores.json` y luego `proveedores.zip`)*

## Relacionado con:
*   [--sql](param_sql.md): Para ver resultados en pantalla sin exportar.
*   [Volver al Índice](index.md)
