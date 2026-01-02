# Parámetro: --reset

El parámetro `--reset` (o alias `-r`) proporciona funcionalidades para reiniciar estados de la aplicación, principalmente relacionados con logs o cachés.

## Sintaxis

```bash
s50info --reset "OPCION"
s50info -r "OPCION"
```

## Detalles Técnicos

*   **Tipo**: String.
*   **Requerido**: No.
*   **Opciones Comunes**:
    *   `log`: Borra o rota los archivos de log actuales.
    *   `force`: Puede forzar ciertas reinicializaciones de configuración (depende de la versión).

## Ejemplos de Uso

### Limpiar logs antes de una operación grande
```bash
s50info --reset log
```

## Relacionado con:
*   [Volver al Índice](index.md)
