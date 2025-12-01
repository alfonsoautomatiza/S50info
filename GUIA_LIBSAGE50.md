# Guía de la API libsage50.py

## Visión General

`libsage50.py` es el módulo principal que proporciona una interfaz simplificada para interactuar con bases de datos Sage50. Utiliza la arquitectura refactorizada del paquete `apiSAGE50` manteniendo compatibilidad con la API original.

## Funciones Principales (Nivel Global)

### `generar_contraseña(codigo_licencia: str) -> str`
- **Propósito**: Genera contraseñas para SQL Server basadas en el código de licencia de Sage50
- **Uso**: `password = generar_contraseña("SZ012345XD67890S")`
- **Retorna**: Contraseña en formato "sage.ew#XXX&YYY"
- **Utilizado en**: `proceso.py`, `libsage50.py` (método `ventana_avanzado`)

---

## Clases

### 1. `confsage50` - Clase de Configuración
- **Propósito**: Gestiona la configuración del sistema Sage50
- **Atributos principales**:
  - `confini`: Objeto de configuración de libwertyconfig
  - `auth_windows`: Indica si se usa autenticación Windows
- **Uso**: `config = confsage50(ficheroini="config.ini")`

---

### 2. `apiSAGE50` - Clase Principal de Interacción

#### Constructor `__init__(conf, para, dirconfig, addonlog, carencia_check, app)`
- **Propósito**: Inicializa la conexión con Sage50
- **Parámetros clave**:
  - `carencia_check`: Si es `True`, omite verificación de licencia
  - `app`: Código de aplicación (defecto "AS5")

#### Atributos de Instancia
- `lconecto`: Booleano que indica si la conexión fue exitosa
- `conexion`: Objeto de conexión pyodbc
- `crsr`: Cursor para ejecutar consultas
- `comunes`: Base de datos comunes activa (ej: "COMU0001")
- `lasterror`: Último error ocurrido

---

## Métodos Principales de `apiSAGE50`

### Métodos de Conexión

#### `conexiondatosini() -> bool`
- **Propósito**: Inicializa y establece la conexión completa con la base de datos
- **Retorna**: `True` si la conexión fue exitosa
- **Uso**: Automáticamente llamado en el constructor
- **Proceso**:
  1. Carga configuración del terminal
  2. Carga configuración del servidor
  3. Establece conexión SQL
  4. Valida base de datos comunes

#### `_load_terminal_config() -> bool` *(Privado)*
- **Propósito**: Carga configuración desde el terminal Sage50
- **Retorna**: `True` si la configuración se cargó correctamente

#### `_load_server_config() -> bool` *(Privado)*
- **Propósito**: Carga configuración del servidor desde cfgclisrv.xml
- **Retorna**: `True` si la configuración se cargó correctamente

#### `_establish_connection() -> bool` *(Privado)*
- **Propósito**: Establece conexión con SQL Server (SQL Auth o Windows Auth)
- **Retorna**: `True` si la conexión fue exitosa

#### `_validate_comunes() -> bool` *(Privado)*
- **Propósito**: Valida la base de datos comunes y obtiene información
- **Retorna**: `True` si los comunes son válidos

---

### Métodos de Consulta SQL

#### `sqltodic(execute: str, params: tuple | list | None = None, lcabecera: bool = False) -> list[dict[str, Any]]`
- **Propósito**: Ejecuta consulta SQL y devuelve resultados como lista de diccionarios
- **Uso**: `results = api.sqltodic("SELECT * FROM #articulo WHERE codigo = ?", ("ART001",))`
- **Retorna**: Lista de diccionarios con los resultados
- **Parámetros**:
  - `execute`: Consulta SQL a ejecutar
  - `params`: Parámetros opcionales para la consulta
  - `lcabecera**: Si `True` y no hay resultados, devuelve dict con `None`

#### `w_codi_sql(sql: str, tbyear: str | list[str], sqlcomun: str, sqlwhere: str = "", sqlgroup: str = "") -> str`
- **Propósito**: Genera consulta SQL con formato Sage50 para múltiples años
- **Uso**: `sql = api.w_codi_sql("SELECT * FROM #articulo", ["2024EJ", "2025EJ"], "COMU0001")`
- **Retorna**: Consulta SQL completa con años procesados
- **Características**:
  - Soporta placeholders (#, ç, COMUNES!)
  - Maneja múltiples años fiscales

#### `vacio_sql(sql: str, lrespuesta: bool = True) -> bool | list`
- **Propósito**: Ejecuta consulta SQL y verifica si está vacía
- **Uso**: `empty = api.vacio_sql("SELECT * FROM #articulo WHERE codigo = ?", True)`
- **Retorna**: `bool` si `lrespuesta=True`, lista de resultados si `False`

---

### Métodos de Utilidad

#### `SAGE50year(database_year: str | int = "", ltabla: bool = False) -> list[str]`
- **Propósito**: Obtiene lista de años disponibles según especificación
- **Uso**:
  - `api.SAGE50year("+")` → Último año
  - `api.SAGE50year("*")` → Todos los años
  - `api.SAGE50year("2024")` → Año específico
- **Retorna**: Lista de años que cumplen la especificación (ej: `['2024EJ', '2025EJ']`)

#### `dict_a_obj(d: dict | list[dict]) -> Any`
- **Propósito**: Convierte diccionario(s) a SimpleNamespace con claves en MAYÚSCULAS
- **Uso**: `obj = api.dict_a_obj({"codigo": "ART001", "nombre": "Producto"})`
- **Retorna**: SimpleNamespace o lista de SimpleNamespace

#### `a_comunes_4(s: str) -> str`
- **Propósito**: Normaliza el código de comunes a formato COMU####
- **Uso**: `comunes = api.a_comunes_4("1")` → `"COMU0001"`
- **Retorna**: Código de comunes normalizado

---

### Métodos de Información

#### `get_mssql_version() -> str` ⭐ *UTILIZADO*
- **Propósito**: Obtiene la versión de SQL Server
- **Uso**: `version = api.get_mssql_version()`
- **Retorna**: String con versión del servidor
- **Utilizado en**: `proceso.py:58`

#### `extraex50() -> str` ⭐ *UTILIZADO*
- **Propósito**: Extrae el código de registro de Sage50
- **Uso**: `registro = api.extraex50()` (llamado internamente)
- **Retorna**: Código de registro o "DEMO"
- **Utilizado en**: Constructor de `apiSAGE50`

#### `obtener_nombre_por_codigo(codigo: str) -> tuple | None`
- **Propósito**: Obtiene el nombre de comunes por código
- **Uso**: `nombre = api.obtener_nombre_por_codigo("0001")`
- **Retorna**: Tuple con nombre o `None`
- **Utilizado en**: Internamente por `_validate_comunes`

#### `obtener_year_comunes() -> list[str]`
- **Propósito**: Obtiene lista de años disponibles en comunes
- **Uso**: `years = api.obtener_year_comunes()`
- **Retorna**: Lista de años (ej: `['2023EJ', '2024EJ']`)
- **Utilizado en**: Internamente por varios métodos

---

### Métodos de UI (Compatibilidad)

#### `ventana_terminal() -> bool` ❌ *NO UTILIZADO*
- **Propósito**: Muestra ventana de configuración del terminal
- **Retorna**: Booleano indicando si se realizó configuración
- **Estado**: No se utiliza en ninguna parte del proyecto

#### `ventana_avanzado() -> bool` ❌ *NO UTILIZADO*
- **Propósito**: Muestra ventana de configuración avanzada
- **Retorna**: Booleano indicando si se confirmó configuración
- **Estado**: No se utiliza en ninguna parte del proyecto

---

### Métodos de Schema

#### `esquemasql2json(tables: str | list[str], database: str = "EUROWINSYS") -> str` ❌ *NO UTILIZADO*
- **Propósito**: Obtiene el esquema de tablas en formato JSON
- **Uso**: `schema = api.esquemasql2json("articulo,cliente")`
- **Retorna**: JSON con esquema de tablas
- **Estado**: No se utiliza en ninguna parte del proyecto

---

## Patrón de Uso Típico

```python
from libsage50 import apiSAGE50

# Crear instancia
api = apiSAGE50()

# Verificar conexión
if api.lconecto:
    # Ejecutar consulta simple
    results = api.sqltodic("SELECT * FROM #articulo")
    print(f"Encontrados {len(results)} artículos")

    # Ejecutar consulta con parámetros
    articulo = api.sqltodic("SELECT * FROM #articulo WHERE codigo = ?", ("ART001",))

    # Consulta multi-año
    sql = api.w_codi_sql("SELECT * FROM #articulo", ["2024EJ", "2025EJ"], "COMU0001")
    results = api.sqltodic(sql)

    # Verificar si está vacía una tabla
    empty = api.vacio_sql("SELECT * FROM #facturas WHERE fecha >= ?", ("2024-01-01",))
else:
    print(f"Error de conexión: {api.lasterror}")
```

## Clases y Funciones NO UTILIZADAS (A Eliminar)

### Métodos sin uso detectado:
- `ventana_terminal()` - `libsage50.py:884`
- `ventana_avanzado()` - `libsage50.py:893`
- `esquemasql2json()` - `libsage50.py:837`

### Métodos con uso confirmado:
- `generar_contraseña()` - Utilizado en `proceso.py` y `libsage50.py`
- `get_mssql_version()` - Utilizado en `proceso.py:58`
- `extraex50()` - Utilizado internamente
- Todos los demás métodos son esenciales para el funcionamiento