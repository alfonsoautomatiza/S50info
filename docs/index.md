# S50Info — CLI para Consultas y Exportación de SAGE50

**S50Info** es una herramienta de consola gratuita para ejecutar consultas SQL contra SAGE50, exportar resultados a múltiples formatos y automatizar tareas técnicas desde línea de comandos.

> **¿Necesitás informes visuales?** Usá [Sage50BI](https://sage50eia.com) que tiene plantillas gratuitas.

---

## Instalación

### 1. Descargar y extraer

Descargar el ZIP desde releases y extraer en `C:\S50Info\`.

### 2. Configurar `config.ini`

```ini
[API]
direccion_servidor = MI_SERVIDOR\MI_INSTANCIA
nombre_usuario = mi_usuario
password = mi_password
driver_servidor = SQL Server Native Client 11.0
terminal = c:\Sage50\Sage50Term
comunes = 4
autenticacion_sql = False

[CONFIG_SAGE50]
empresa = 01
usuario = ADMIN
password =
```

### 3. Verificar instalación

```bash
s50info.exe info
```

---

## Comandos

| Comando | Descripción |
|---------|------------|
| `info` | Muestra información de conexión activa |
| `sql` | Ejecuta SQL y muestra resultado en consola |
| `export` | Ejecuta SQL y exporta a archivo |
| `run` | Ejecuta scripts Python con contexto SAGE50 |
| `reset` | Trunca logs del sistema |

---

## Ejemplos de Uso

### Información de conexión

```bash
s50info info
s50info info --grupo-comunes 4
```

Sin argumentos, muestra: servidor, comunes, años disponibles, versión SQL.

### Consulta básica

```bash
s50info sql "SELECT * FROM #clientes"
```

Equivalente en SQL Server: executed against `GESTION{año}.dbo.clientes`.

### Consulta con year específico

```bash
s50info sql "SELECT * FROM #clientes" --sqlyear 2025JX
```

### Consulta todos los años

```bash
s50info sql "SELECT * FROM #clientes" --sqlyear @
```

El símbolo `@` evita que el shell expanda `*` a archivos.

### Agrupar resultados de varios años

```bash
s50info sql "SELECT CODIGO, MAX(NOMBRE) FROM #clientes" --sqlyear @ --groupby CODIGO
```

Útil para consolidar el mismo registro que existe en varios ejercicios.

### Ver consulta en sintaxis SAGE50

```bash
s50info sql "SELECT * FROM #clientes" --sage50
```

Muestra: `SELECT * FROM GESTION!clientes`.

### Tablas de comunes

```bash
s50info sql "SELECT * FROM [COMU]gruposemp"
s50info sql "SELECT * FROM [COMU]gruposemp" --grupo-comunes 4
```

`[COMU]tabla` → `COMU0004.dbo.tabla`.

### Exportar a CSV

```bash
s50info export "SELECT * FROM #clientes" --formato csv --output clientes
```

Output: `clientes.csv`.

### Exportar a Excel

```bash
s50info export "SELECT * FROM #articulos" --formato xlsx --output articulos
```

Output: `articulos.xlsx`.

### Exportar a JSON

```bash
s50info export "SELECT * FROM #clientes" --formato json
```

### Exportar y comprimir

```bash
s50info export "SELECT * FROM #clientes" --formato csv --zip
```

Output: `clientes.csv.zip`.

### Ejecutar scripts

```bash
# Un script específico
s50info run script\mi_script.py

# Todos los .py de una carpeta
s50info run script\
```

### Resetear logs

```bash
s50info reset
```

---

## Sintaxis SQL

### Tablas de gestión

| Sintaxis | Equivalente |
|----------|------------|
| `#clientes` | `GESTION!clientes` (año actual) |
| `#clientes` + `--sqlyear 2024JX` | `GESTION2024JX.dbo.clientes` |
| `#clientes` + `--sqlyear @` | UNION de todos los años |

### Tablas comunes

| Sintaxis | Equivalente |
|----------|------------|
| `[COMU]tabla` | `COMU0004.dbo.tabla` |
| `COMUNES!tabla` | Igual que `[COMU]tabla` |

### Años fiscales

| Valor | Significado |
|-------|-----------|
| `+` | Último año (por defecto) |
| `*` | Todos los años |
| `@` | Todos los años (sin expansión shell) |
| `2025JX` | Un año específico |
| `2024JX,2025JX` | Lista separada por coma |

---

## Opciones

### Globales

| Opción | Alias | Descripción |
|--------|------|------------|
| `--grupo-comunes` | `-c` | Grupo de comunes |
| `--pausa` / `--no-pausa` | — | Pausar al final |

### Consulta/Exportación

| Opción | Alias | Descripción |
|--------|------|------------|
| `--sqlyear` | `-a` | Año(s) |
| `--grupo-comunes` | `-c` | Grupo de comunes |
| `--groupby` | `-b` | Campo para agrupar |
| `--sage50` | `-s` | Mostrar sintaxis SAGE50 |
| `--formato` | `-f` | Formato: txt, csv, json, xml, xlsx |
| `--output` | `-o` | Nombre de archivo |
| `--plantilla` | `-t` | Plantilla TXT |
| `--zip` | `-z` | Comprimir |

---

## Plantillas BI (BI_QUERIES)

El proyecto incluye consultas prédefinidas llamadas **samples** o **plantillas BI**. Se accede desde scripts Python, no desde CLI.

### Listar samples disponibles

```python
# En un script ejecutado con s50info run
from s50script import samples_disponibles

items = samples_disponibles()
for item in items:
    print(f"{item['nombre']}: {item['titulo']}")
    print(f"  {item['descripcion']}")
```

### Samples disponibles

| Nombre | Título | Descripción |
|--------|-------|-------------|
| `DetalleCargaCamion` | Carga reparto por cliente | Carga de camión basada en etiquetas de envío y albanes de venta |
| `DeudaPorVendedor` | Deuda Por Vendedor | Deuda pendiente por vendedor y porcentaje sobre total |
| `CuotasClienteConcepto` | Cuotas Cliente Concepto | Cuotas por cliente y concepto vigentes |
| `Ventas_Dto_Cliente_Articulo` | Ventas Dto Cliente Articulo | Ventas con descuento medio ponderado por familia, artículo, cliente |
| `Carga_Reparto_por_cliente` | Carga reparto por cliente | Consulta combinada de albaranes, clientes, artículos, familias |
| `Rentabilidad_albaran_lote` | Rentabilidad albarán y lote | Detalle completo con beneficio, coste prorrateado por lotes |
| `Ventas_Vendores_por_ranking` | Ventas Vendedores ranking | Ranking de ventas por vendedor y ejercicio |
| `Deuda_plazo_medio_vendedor_mes` | Deuda y plazo medio | Deuda pendiente y plazo medio de cobro por vendedor y mes |

### Usar un sample

```python
from s50script import samplebi

# Cargar un sample específico
datos = samplebi("DetalleCargaCamion")
print(f"Registros: {len(datos)}")

# Sobrescribir parámetros
datos = samplebi("DetalleCargaCamion", sqlyear="@", groupby="Codigo_Etiqueta")
```

### Ejecutar con query_to_dict

```python
from s50script import query_to_dict

# Query personalizada
datos = query_to_dict("SELECT * FROM #clientes")
print(f"Clientes: {len(datos)}")

# Con year específico
datos = query_to_dict("SELECT * FROM #clientes", sqlyear="2025JX")

# Multi-year con groupby
datos = query_to_dict(
    "SELECT CODIGO, MAX(NOMBRE) FROM #clientes",
    sqlyear="@",
    groupby="CODIGO"
)
```

---

## Scripts de Ejemplo

La carpeta `script/` contiene ejemplos Formativos.

### 1. Exportación de artículos

**Archivo:** `script/exportacion_articulos.py`

```bash
s50info run script/exportacion_articulos.py
```

Este script demuestra:
- `query_to_dict()` para obtener datos
- Control de years (`+`, `@`, año concreto)
- Agrupación con `groupby`
- Exportación multiformato (`xlsx`, `csv`, `json`, `xml`, `txt`)

Funciones disponibles:
- `exportar_articulos_base()` — año actual → Excel
- `exportar_articulos_por_year()` — año concreto → CSV
- `exportar_articulos_multi_year_agrupados()` — todos años → JSON
- `exportar_formatos_posibles()` —demo de formatos

### 2. Selección interactiva de samples

**Archivo:** `script/ejemplo_lite_sage50bi.py`

```bash
s50info run script/ejemplo_lite_sage50bi.py
```

Este script demuestra:
- `seleccionar_samples()` — selector interactivo por consola
- `exportar_samples()` — exportar varios samples
- `imprimir_diccionarios()` — formato de salida

Interfaz interactiva:
- Flechas: mover cursor
- Espacio: marcar/desmarcar
- T: seleccionar todos
- N: deseleccionar todos
- Enter: confirmar

### 3. Ver y resetear logs

**Archivo:** `script/visualizar_log_analisis_excel_reseteo.py`

```bash
s50info run script/visualizar_log_analisis_excel_reseteo.py
```

Este script demuestra:
- Consulta directa a `EUROWINSYS.dbo.log_analisis`
- Exportación a Excel
- Confirmación antes de `reset_log()`

Útil para auditar antes de borrar.

---

## API Python (para scripts)

Al ejecutar `s50info run script/xxx.py`, el script tiene acceso a:

### Objeto `proceso`

```python
#属性
proceso.api           # objeto apiSAGE50
proceso.exportador   # ExportadorResultados

# Métodos
proceso.query_to_dict(sql, sqlyear="+", grupo_comunes=None, groupby=None)
proceso.imprimir_diccionarios(datos, formato="txt", nombre_archivo=None, comprimir=False)
proceso.reset_log()
proceso.info(pausa=False, grupo_comunes=None)

# Métodos helpers (inyectados)
proceso.samplebi(nombre, sqlyear=None, grupo_comunes=None, groupby=None)
proceso.query_to_dict(sql, sqlyear="+", grupo_comunes=None, groupby=None, fast_build=False)
proceso.samples_disponibles()
proceso.seleccionar_samples()
proceso.exportar_samples(nombres)
```

### Funciones globales (builtins)

```python
# Estas están disponibles sin importar:
s50info_proceso         # referencia al objeto proceso
samplebi(nombre)       # cargar un sample
query_to_dict(sql)     # ejecutar SQL
samples_disponibles() # listar samples
seleccionar_samples() # selector interactivo
exportar_samples(nombres) # exportar varios
```

### Método apiSAGE50

```python
#属性
proceso.api.comunes       # grupo de comunes activo
proceso.api.tbyear     # años disponibles
proceso.api.lconecto    # estado de conexión

# Métodos
proceso.api.consulta(sql)           # ejecutar consulta simple
proceso.api.sql_to_list(sql)       # como lista de diccionarios
proceso.api.build_query(...)       # construir query multi-year
```

---

## Errores Comunes

| Error | Causa | Solución |
|-------|--------|----------|
| `No se pudo conectar con SAGE50` | Credenciales incorrectas en config.ini | Verificar usuario/password |
| `Error de conexión ODBC` | Driver no instalado | Instalar SQL Server Native Client 11.0 |
| `No se encontraron años` | Grupo de comunes incorrecto | Verificar `--grupo-comunes` |
| `La tabla no existe` | Nombre incorrecto | Usar `--sage50` para ver equivalencia |
| `El archivo no es .py` | Extensión incorrecta | Usar archivo `.py` |
| `No se encontró script` | Ruta incorrecta | Verificar ruta relativa a `script/` |

---

## Configuración Avanzada

### Múltiples configuraciones

Crear múltiples archivos `config.ini` y usar mediante copia:

```bash
copy config.ini config.ini.backup
copy config_prod.ini config.ini
s50info info
```

### Variables de entorno

Crear `.env` para Sobrescribir valores:

```env
SAGE50_SERVIDOR=OTRO_SERVIDOR\INSTANCIA
SAGE50_USUARIO=otro_usuario
SAGE50_PASSWORD=otra_password
DEBUG=True
```

### Plantillas TXT personalizadas

```bash
s50info export "SELECT * FROM #clientes" --formato txt --plantilla mi_plantilla.txt --output clientes
```

Plantilla con marcadores `{CAMPO}`.

---

## Integración

### Programador de tareas (Windows)

```xml
<action with="s50info.exe export">
  <command>"SELECT * FROM #clientes" --formato csv --output clientes_diarios --zip</command>
  <workingDirectory>C:\S50Info</workingDirectory>
</action>
```

### PowerShell

```powershell
# Exportación diaria
& .\s50info.exe export "SELECT * FROM #clientes WHERE FECHA > GETDATE()-7" --formato csv --output clientes_nuevos
```

### .bat

```bat
@echo off
s50info export "SELECT * FROM #articulos" --formato csv --output articulos_diarios
if errorlevel 1 (
    echo Error en exportacion
    exit /b 1
)
```

---

## Siguiente Paso

¿Necesitás más opciones visuales? Probá [Sage50BI](https://sage50eia.com/s50info) — tiene plantillas gratuitas.

---

## Referencia Rápida

```
s50info info                           # Ver conexion
s50info sql "SELECT * FROM #clientes" # Consulta rapida
s50info export "SELECT * FROM #clientes" --formato csv --output clientes
s50info run script\mi_script.py       # Ejecutar script
s50info reset                         # Resetear logs
```

---

## FAQ

### ¿Puedo usar con SQL Server Authentication?

Sí: `autenticacion_sql = True` en config.ini.

### ¿Puedo conectar a múltiples empresas?

Sí: usar `--grupo-comunes` para cambiar el grupo de comunes en cada ejecución.

### ¿Puedo ejecutar queries de escritura?

No. Solo `SELECT` y `WITH` están permitidos por seguridad.

### ¿Dónde se guardan los archivos?

En la carpeta actual de ejecución. Usar `--output` para especificar nombre.

### ¿Necesito Python instalado?

No. El ejecutable es autónoma (PyInstaller).