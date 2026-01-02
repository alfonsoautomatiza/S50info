# Parámetro: --clave

El parámetro `--clave` (o alias `-c`) es una utilidad de seguridad para recuperar la contraseña de acceso SQL de la instalación de Sage50.

## Sintaxis

```bash
s50info --clave
s50info -c
```

## Detalles Técnicos

*   **Tipo**: Flag (Booleano) o String (opcionalmente puede aceptar un valor en algunas implementaciones internas, pero generalmente se usa como flag).
*   **Comportamiento**:
    *   Lee la configuración de licencia y seguridad de Sage50.
    *   Decodifica y muestra en pantalla la clave de usuario SQL o la cadena de conexión necesaria para aplicaciones externas.

## Ejemplos de Uso

### Recuperar clave
```bash
s50info --clave
```
*(Salida esperada: `Clave SQL: XXXXX-YYYYY-ZZZZZ`)*

## Relacionado con:
*   [Volver al Índice](index.md)
