# Parámetro: --comprimir

El parámetro `--comprimir` (o alias `-z`) indica a S50Info que debe comprimir el archivo de salida resultante en un archivo ZIP.

## Sintaxis

```bash
s50info --sql2doc "SQL" [OPCIONES] --comprimir
s50info -d "SQL" [OPCIONES] -z
```

## Detalles Técnicos

*   **Tipo**: Flag (Booleano). Sin valor.
*   **Requerido**: No.
*   **Comportamiento**:
    1.  Genera el archivo de exportación normal (ej. `datos.json`).
    2.  Crea un archivo ZIP (ej. `datos.zip`) que contiene el archivo generado.
    3.  (Opcional, depende de implementación interna) Puede eliminar el archivo original para ahorrar espacio.

## Ejemplos de Uso

### Exportar Excel y comprimir
Ideal para envíos por correo o almacenamiento:
```bash
s50info -d "SELECT * FROM DIARIO" -f xlsx -o diario_2024 -z
```
*(Resultado final: `diario_2024.zip`)*

## Relacionado con:
*   [--sql2doc](param_sqltodic.md): Comando de exportación.
*   [Volver al Índice](index.md)
