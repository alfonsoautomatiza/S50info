# Parámetro: --noupdate

El parámetro `--noupdate` (o alias `-no`) permite omitir el proceso automático de verificación y descarga de actualizaciones al iniciar S50Info.

## Sintaxis

```bash
s50info [OTROS_COMANDOS] --noupdate "MOTIVO"
s50info [OTROS_COMANDOS] -no "MOTIVO"
```

## Detalles Técnicos

*   **Tipo**: String.
*   **Requerido**: No.
*   **Valor**: Debe proporcionarse una cadena de texto explicando el motivo (aunque sea breve) por el cual se salta la actualización. Esto puede quedar registrado en logs para auditoría.
*   **Uso**:
    *   Acelera el inicio de la aplicación en entornos de desarrollo o cuando se sabe que no hay conexión a internet.
    *   Evita interrupciones en scripts automatizados.

## Ejemplos de Uso

### Ejecución rápida en desarrollo
```bash
s50info -s "SELECT 1" --noupdate "dev_mode"
```

## Relacionado con:
*   [Volver al Índice](index.md)
