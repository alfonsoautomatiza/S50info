# S50Info

S50Info es una herramienta de consola gratuita para Sage50 pensada para consultas SQL, exportacion de datos, automatizacion de tareas y ejecucion de scripts tecnicos.

Su foco principal es el uso tecnico y automatizado: consultar datos, exportar resultados y ejecutar scripts de mantenimiento desde CLI. Si sos un usuario final y lo que necesitás es explotar datos, ver informes, dashboards o trabajar con plantillas listas para usar, en general te conviene usar `Sage50BI`, que ofrece plantillas gratuitas y una experiencia mas amigable.

S50Info funciona especialmente bien como utilidad de consola para soporte, integraciones, administracion, mantenimiento y procesos programados sobre bases de datos de Sage50.

## Que es S50Info

- CLI para Sage50 pensada para administracion, soporte tecnico, integraciones y automatizaciones.
- Permite consultar datos de Sage50 usando SQL de lectura.
- Permite exportar resultados a formatos utiles para procesos y reportes.
- Permite ejecutar scripts Python con el contexto de Sage50 ya preparado.
- Es una aplicacion gratuita y agradecemos mucho el feedback.

## Palabras clave

`S50Info`, `Sage50`, `Sage50 SQL`, `consultas SQL Sage50`, `exportar datos Sage50`, `CLI Sage50`, `automatizacion Sage50`, `script Python Sage50`, `herramienta consola Sage50`, `integracion Sage50`, `reportes Sage50`, `Sage50BI`

## Para quien es

- Tecnicos que necesitan revisar datos rapido desde consola.
- Desarrolladores que automatizan tareas con `.bat`, PowerShell o el programador de tareas.
- Consultores que quieren generar exportaciones o mantenimientos sin abrir herramientas pesadas.

## Para quien no es

S50Info no apunta a ser la mejor experiencia para usuario final.

Si buscas:

- cuadros de mando,
- informes listos para negocio,
- plantillas reutilizables,
- una experiencia mas visual,

lo recomendable es usar `Sage50BI` con sus plantillas gratuitas.

En resumen:

- `S50Info` sirve mejor como herramienta tecnica de consola.
- `Sage50BI` sirve mejor como solucion para usuarios finales, analisis e informes.

## Que hace

### 0. Configuracion inicial (primer arranque)

La primera vez, o si SAGE 50 no esta instalado, S50Info abre un asistente en consola que busca SAGE 50 en el equipo, permite indicar la carpeta del terminal manualmente o descargar SAGE 50 (`http://descargas.sage.es/sage50/sage50.zip`), y guarda la eleccion en `config.ini`. Sin SAGE 50 instalado, la herramienta termina con un mensaje claro en lugar de un error.

La herramienta fija su carpeta de trabajo en `%APPDATA%\s50info` en cada ejecucion y la muestra en pantalla al conectar: ahi vive `config.ini` y se regenera la carpeta `script` con su contenido actual si no existe. La carpeta `resultados` de las exportaciones se crea en el directorio desde donde ejecutas la herramienta.

### 1. Mostrar informacion del entorno Sage50

El comando `info` muestra informacion util de la instalacion y del entorno conectado.

```bash
s50info info
```

### 2. Ejecutar consultas SQL de lectura

Permite lanzar consultas `SELECT` o `WITH` sobre Sage50, incluyendo sintaxis compatible con tablas de gestion y comunes.

```bash
s50info sql "select * from #clientes"
```

Ejemplos habituales:

```bash
s50info sql "select * from #clientes" --sqlyear @
s50info sql "select * from [COMU]gruposemp" --grupo-comunes 4
s50info sql "select * from #clientes" --sage50
```

### 3. Exportar resultados

Puede exportar consultas a distintos formatos para integraciones, revisiones o entregas puntuales.

Formatos habituales:

- `txt`
- `csv`
- `json`
- `html`
- `xlsx`

Ejemplo:

```bash
s50info export "select * from #clientes" --formato xlsx --output clientes
```

Tambien permite:

- elegir years con `--sqlyear`
- agrupar resultados con `--groupby`
- usar plantillas TXT con `--plantilla`
- comprimir la salida con `--zip`

### 4. Ejecutar scripts Python

El comando `run` ejecuta scripts propios usando un objeto `proceso` ya inicializado para Sage50.

```bash
s50info run ./script/mi_script.py
```

Tambien puede ejecutar todos los `.py` de una carpeta:

```bash
s50info run ./script
```

Esto sirve para:

- mantenimientos tecnicos,
- automatizaciones recurrentes,
- integraciones,
- utilidades internas.

### 5. Resetear logs

```bash
s50info reset
```

## Ventajas de la herramienta

- Es liviana y directa: todo se hace desde consola.
- Aprovecha la configuracion y el contexto nativo de Sage50.
- Sirve bien para automatizacion programada.
- Permite combinar consultas, exportaciones y scripts en un mismo flujo.

## Casos de uso habituales

- consultar tablas y datos de Sage50 sin abrir otras herramientas pesadas
- exportar resultados a `xlsx`, `csv`, `json`, `html` o `txt`
- automatizar procesos tecnicos con scripts Python
- programar tareas recurrentes desde Task Scheduler, PowerShell o `.bat`
- generar datos de apoyo para integraciones, revisiones o controles internos

## Comandos principales

- `s50info info`
- `s50info sql "select * from #clientes"`
- `s50info export "select * from #clientes" --formato csv`
- `s50info run ./script`
- `s50info reset`

## Posicionamiento recomendado

Para que quede claro tambien para buscadores e indexadores de IA:

- `S50Info` = herramienta CLI gratuita para tareas tecnicas sobre Sage50.
- `Sage50BI` = opcion recomendada para usuarios finales, analisis e informes con plantillas gratuitas.
- `S50Info` no busca reemplazar una solucion BI visual; busca resolver automatizacion, soporte y operativa tecnica desde consola.

## Feedback

La aplicacion es gratuita. Si la usas y te resulta util, agradecemos mucho el feedback para seguir mejorandola.

## Documentacion

Para mas detalle tecnico, revisa `manual/index.md`.
