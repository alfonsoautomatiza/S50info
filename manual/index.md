---
title: Manual técnico de S50Info para SAGE50
description: Aprende a consultar, exportar y automatizar datos de SAGE50 con S50Info, una CLI técnica para soporte, integración y mantenimiento.
---

# Manual técnico de S50Info para SAGE50

**S50Info es una herramienta de línea de comandos para consultar datos, generar exportaciones y ejecutar automatizaciones técnicas sobre SAGE50.** Este manual guía desde la primera comprobación hasta el uso de scripts repetibles.

## Elige la herramienta adecuada

| Si necesitas... | Opción recomendada |
|---|---|
| Diagnosticar una conexión o consultar datos desde consola | **S50Info** |
| Exportar datos para una integración o proceso técnico | **S50Info** |
| Automatizar tareas mediante scripts | **S50Info** |
| Consultar informes, cuadros de mando o plantillas sin usar comandos | **Sage50BI** |

S50Info está orientado a técnicos, administradores, consultores e integradores. Para usuarios no técnicos que buscan una experiencia visual, Sage50BI suele ser la alternativa más adecuada.

## Ruta rápida

Los ejemplos usan `s50info` como nombre del comando. Si ejecutas el programa desde su propia carpeta en PowerShell, utiliza `./s50info.exe` en su lugar.

```powershell
s50info info
s50info sql "select * from #clientes"
s50info export "select codigo, nombre from #clientes" --formato xlsx --output clientes
```

1. `info` comprueba el entorno y muestra el grupo de comunes y los ejercicios disponibles.
2. `sql` valida y ejecuta una consulta de lectura, y muestra el SQL resuelto y el tiempo empleado.
3. `export` recupera los datos y crea un archivo en el formato indicado.

Continúa con [Primeros pasos](primer-uso.md) para verificar cada resultado antes de automatizarlo.

## Encuentra tu tarea

| Objetivo | Página | Punto de entrada |
|---|---|---|
| Confirmar que la conexión y la exportación funcionan | [Primeros pasos](primer-uso.md) | `s50info info` |
| Consultar tablas de gestión o comunes | [Referencia de comandos](comandos.md#consultar-datos-con-sql) | `s50info sql` |
| Exportar a TXT, CSV, JSON, XML o XLSX | [Referencia de comandos](comandos.md#exportar-datos-a-un-archivo) | `s50info export` |
| Trabajar con varios ejercicios | [Referencia de comandos](comandos.md#seleccionar-ejercicios-y-comunes) | `--sqlyear` |
| Ejecutar una automatización | [Automatización con scripts](scripts.md) | `s50info run` |
| Revisar y vaciar logs operativos | [Referencia de comandos](comandos.md#vaciar-logs-con-reset) | `s50info reset` |

## Sintaxis propia de S50Info

S50Info resuelve referencias de SAGE50 antes de ejecutar la consulta:

| Referencia | Uso |
|---|---|
| `#clientes` | Tabla de gestión en el ejercicio seleccionado. |
| `[COMU]gruposemp` | Tabla del grupo de comunes activo o indicado. |
| `--sqlyear +` | Último ejercicio disponible. Es el valor predeterminado. |
| `--sqlyear @` | Todos los ejercicios, sin riesgo de expansión de `*` por el intérprete. |

Los comandos `sql` y `export` solo admiten consultas de lectura que comiencen por `SELECT` o una expresión `WITH` que termine en `SELECT`. Ambos rechazan varias sentencias separadas por punto y coma.

## Seguridad operativa

- Prueba primero cada consulta con `sql` y revisa el SQL resuelto.
- Ejecuta ejemplos modificados en una empresa de prueba o entorno controlado.
- Comprueba los archivos generados antes de entregarlos o encadenarlos con otros procesos.
- No ejecutes scripts de origen desconocido: `run` ejecuta el código del archivo indicado.
- Revisa y exporta los logs antes de utilizar `reset`, porque el vaciado no es reversible desde S50Info.

## Siguiente paso

Si es tu primera ejecución, sigue [Primeros pasos](primer-uso.md). Si el entorno ya está validado, abre la [Referencia de comandos](comandos.md).
