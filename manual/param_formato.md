# Parámetro: --formato

El parámetro `--formato` (o alias `-f`) especifica el formato del archivo de salida generado por la opción `sql2doc`.

## Sintaxis

```bash
s50info --sql2doc "SQL" --formato [txt|xlsx|json|csv|html]
s50info -d "SQL" -f [txt|xlsx|json|csv|html]
```

## Detalles Técnicos

*   **Tipo**: String (Opciones limitadas).
*   **Valor por defecto**: `txt`.
*   **Opciones Disponibles**:
    *   `txt`: Archivo de texto plano. Puede usar plantillas.
    *   `xlsx`: Hoja de cálculo de Excel.
    *   `json`: Archivo JSON (Array de objetos).
    *   `csv`: Archivo separado por comas.
    *   `html`: Tabla HTML simple.

## Ejemplos de Uso

### Generar Excel
```bash
s50info -d "SELECT * FROM VENTAS" -f xlsx
```

### Generar JSON para integración
```bash
s50info -d "SELECT * FROM STOCK" -f json
```

## Relacionado con:
*   [--sql2doc](param_sqltodic.md): Comando principal que utiliza este formato.
*   [--plantilla](param_plantilla.md): Aplica solo si el formato es `txt`.
*   [Volver al Índice](index.md)
