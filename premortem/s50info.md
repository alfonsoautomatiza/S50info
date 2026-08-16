# S50Info — Resumen funcional completo

## 1. Qué es

**S50Info** es una herramienta de consola (CLI) gratuita para **SAGE50 ERP**, orientada a administradores de sistemas, desarrolladores/integradores y consultores técnicos. Centraliza en un único ejecutable Windows las tareas técnicas más frecuentes sobre las bases de datos SQL Server de SAGE50: consultas SQL de lectura, exportación multiformato, ejecución de scripts Python con contexto SAGE50 ya inicializado, y mantenimiento de logs.

- Producto/paquete: `s50info` (id interno `tool-sage50`)
- Versión de referencia (PRD): `0.1.0`; `c/product.json` reporta `2.1.8`
- Autor: ALCA TIC, S.L.
- Stack: Python 3.13+, Typer, Rich, PyInstaller
- Distribución: ejecutable Windows autónomo (PyInstaller, modo `onedir`), sin necesidad de instalar Python
- Plataforma objetivo: **exclusivamente Windows**
- Producto "hermano" recomendado para usuarios finales: **Sage50BI** (dashboards, informes, plantillas visuales). S50Info explícitamente **no** busca ser esa experiencia visual.

### Para quién es / no es
- **Sí**: técnicos de soporte, administradores de sistemas, desarrolladores que automatizan con `.bat`/PowerShell/Task Scheduler, consultores ERP en auditorías/migraciones.
- **No**: usuarios finales que buscan dashboards, informes de negocio o plantillas listas (para eso está Sage50BI).

## 2. Problema que resuelve

1. Consultas SQL dispersas: evita depender de SSMS para verificaciones puntuales.
2. Exportación manual tediosa (copiar/pegar desde SSMS a Excel).
3. Scripts de mantenimiento desconectados del contexto SAGE50 (cada uno debía replicar la lógica de conexión).
4. Recuperación opaca/manual de credenciales (p. ej. CRM).
5. Distribución compleja de herramientas Python (entornos, dependencias).

## 3. Arquitectura y módulos principales

```
s50info.exe
 ├── s50info.py            → CLI (Typer): parseo de comandos, orquestación
 ├── s50proceso.py          → Core de negocio: SQL, exportación, licencia, info, reset
 ├── s50exportador_resultados.py → Motor de exportación multiformato
 └── s50script.py           → Helpers/queries de ejemplo para scripts `run` (BI samples)
        │
        ├── pysage50e (apiSAGE50) → API oficial SAGE50 (conexión, build_query, execute_query, sql_to_list)
        ├── libwertyconfig        → Gestión de licencia (x11) y config
        └── pyodbc / ODBC          → conexión física a SQL Server
                │
        SQL Server: EUROWINSYS (sistema/logs), COMUxxxx (datos empresa), FMCRM0xx (CRM)
```

Otros ficheros relevantes:
- `config.ini`: configuración de conexión (servidor, usuario, password, driver, terminal, comunes, autenticación SQL, empresa/usuario SAGE50).
- `.env` (opcional, vía `python-dotenv`): sobreescribe variables sensibles; también activa `DEBUG=True/Si/1` para logging detallado (`configure_debug_logging`).
- `licencia.lic`: licencia de la herramienta.
- `script/`: carpeta de ejemplos ejecutables con `run` (`ejemplo_lite_sage50bi.py`, `exportacion_articulos.py`, `visualizar_log_analisis_excel_reseteo.py`).
- `resultados/`: carpeta de salida por defecto del exportador.
- `docs/index.md` + `mkdocs.yml`: documentación técnica publicada (mkdocs gh-deploy).
- `c/`: build (Cython, `build_exe.py`, `product.json`, `RELEASE/`).

## 4. Flujo de conexión / arranque

Al iniciar cualquier comando, `s50info.py::_crear_proceso()`:
1. Instancia `apiSAGE50()` (pysage50e), que se conecta usando `config.ini`.
2. Instancia `s50proceso.proceso(api=api_obj)`, que:
   - Evalúa la **licencia** vía `libwertyconfig.x11()`.
     - Hay un **periodo de gracia de 7 días** desde la fecha de creación de `config.ini` (`carencia`), durante el cual no se solicita formulario de contacto.
     - Pasado ese periodo, si la licencia falla o está en modo demo, se abre automáticamente una página de ayuda/contacto (`SAGE50BI_URL`, por defecto `https://sage50eia.com/s50info`), usando `os.startfile` en Windows (robusto en builds PyInstaller) con fallback a `webbrowser.open`.
   - Verifica conexión activa (`api.lconecto`); si falla, registra error y no continúa.
3. Si la conexión falla, se corta la ejecución con mensaje de error.

Existe además un mecanismo de **CTA de uso** (`_record_successful_use_and_maybe_show_cta`): guarda contador de usos exitosos en `%APPDATA%/s50info/usage_prompt.json` y, a partir del 5º uso exitoso y luego cada 20, muestra un mensaje invitando a contactar (con UTM `cli/post_command/s50info_contact`).

## 5. Comandos CLI (Typer)

Invocación general: `s50info [OPCIONES] [COMANDO]`. Sin subcomando, ejecuta `info` por defecto (comportamiento del `@app.callback`).

Opción global compartida: `--grupo-comunes` / `-c` (usable también a nivel de callback principal).

### 5.1 `s50info` (sin comando) / `s50info info`
Muestra información de la conexión activa: configuración (servidor SQL, driver, usuario, terminal, autenticación, comunes, empresa/usuario SAGE50 — password oculto con `********`), tablas GESTION en uso (comunes, nombre, letra), años fiscales disponibles y versión del servidor SQL.

- Opción: `--grupo-comunes` / `-c` — grupo de comunes a usar (si no se indica, se toma de `config.ini`).
- Pausa final ("Presione UNA tecla para continuar...") tras mostrar la info.

### 5.2 `s50info sql "<query>"`
Ejecuta una consulta SQL **de solo lectura** (`SELECT`/`WITH`) contra SAGE50, validando la sintaxis SQL antes de ejecutarla (sin `execute_query(commit=False)`, es decir no persiste cambios).

Opciones:
- `query` (argumento posicional): SQL con sintaxis SAGE50 extendida.
- `--sqlyear` / `-a` (default `"+"`): especificación de años/ejercicios:
  - `+` → último year
  - `*` o `@` → todos los years (usar `@` para evitar que el shell expanda `*` a archivos locales; hay lógica de normalización `_normalizar_sqlyear_desde_shell` que detecta esta expansión accidental y avisa al usuario)
  - year concreto, p. ej. `2025JX`
  - lista separada por comas, p. ej. `2024JX,2025JX`
- `--grupo-comunes` / `-c`: acepta número (`4`) o código completo (`COMU0004`); normalizado internamente.
- `--groupby` / `-b`: agrupa el resultado final tras unir varios years (útil junto con `-a @`).
- `--sage50` / `-s`: además de ejecutar, muestra la consulta equivalente en sintaxis SAGE50 (sustituye `#tabla` → `GESTION!tabla`, `[COMU]tabla` → `COMUNES!tabla`).

Salida por consola: grupo comunes usado, años resueltos, (opcional) agrupación, (opcional) SQL SAGE50, tiempo de ejecución y el SQL válido final.

**Reglas de seguridad SQL** (en `s50proceso._es_sql_lectura_permitido`):
- Solo se permite `SELECT` o `WITH ... SELECT` (valida que un CTE `WITH` realmente termine en un `SELECT`, con parser manual tokenizando paréntesis, comentarios `--`/`/* */` y strings con comillas).
- Se rechazan sentencias con separadores `;` (múltiples sentencias).
- No se permite escritura.

### 5.3 `s50info export "<query>" [opciones]`
Igual que `sql`, pero ejecuta la query y exporta el resultado con `proceso.sql2doc()` → `exportador_resultados.exportar()`.

Opciones adicionales sobre `sql`:
- `--formato` / `-f` (default `txt`): `txt`, `csv`, `json`, `xml`, `xlsx`/`excel` (README también menciona `html`, pero el motor de exportación real solo implementa TXT/CSV/JSON/XML/Excel — `html` no está en `PRODUCT.md`/exportador; se documenta como discrepancia).
- `--output` / `-o`: nombre base del archivo de salida (sin extensión); si no se especifica, se autogenera `sqltodic_<ddMMyyyyHHmm>`.
- `--plantilla` / `-t`: ruta a plantilla TXT personalizada (ver detalle abajo).
- `--zip` / `-z`: comprime el resultado generado en un `.zip` (elimina el archivo original tras comprimir).

### 5.4 `s50info run [ruta] [--skip-polars-cpu-check]`
Ejecuta scripts Python externos con el objeto `proceso` (ya conectado a SAGE50) inyectado en el namespace global del script (`proceso`), además de helpers extra vía `builtins` (ver sección 7).

- `ruta` (opcional): archivo `.py` o carpeta. Si se omite, intenta usar la carpeta `script` automáticamente.
- Si es un directorio: ejecuta todos los `.py` en orden alfabético (`sorted(path.glob("*.py"))`), reportando error por script sin detener los siguientes; si alguno falla, retorna código de salida 1 al final.
- Si es un archivo: valida que exista y que la extensión sea `.py`.
- `--skip-polars-cpu-check` / `--polars-skip-cpu-check`: define `POLARS_SKIP_CPU_CHECK=1` para scripts que usan Polars en hardware antiguo/incompatible.
- Cada script recibe en sus globals: `__name__="__main__"`, `__file__`, `proceso`, y los helpers `samplebi`, `query_to_dict`, `samples_disponibles`, `seleccionar_samples`, `exportar_samples`.

### 5.5 `s50info reset`
Trunca las tablas de logs del sistema en la base `EUROWINSYS`:
```sql
truncate table "EUROWINSYS"."dbo".log_analisis;
truncate table "EUROWINSYS"."dbo".log_error;
```
Sin confirmación adicional ni opciones.

## 6. Sintaxis SQL extendida de SAGE50

El CLI traduce sintaxis "amigable" SAGE50 a SQL Server real según el grupo de comunes y los years activos:

| Sintaxis SAGE50 | Resuelve a |
|---|---|
| `#tabla` (p. ej. `#clientes`) | tabla de gestión (`GESTION!tabla`), resuelta contra el/los year(s) indicados por `--sqlyear` |
| `[COMU]tabla` | tabla del comunes activo (`COMUNES!tabla`) |
| `GESTION!CLIENTES` | sintaxis SAGE50 nativa equivalente |
| `COMUNES!tabla` | ídem para comunes |

- El **grupo de comunes** (`COMU0004`, etc.) determina la base de datos de comunes y los años fiscales disponibles (`api.obtener_year_letra_nombre_comunes`).
- `--sqlyear`/`-a` resuelve una lista de years vía `api.SAGE50year(sqlyear, tyear=...)`.
- Cuando se consultan varios years (`*`/`@`/lista), las tablas `#` se unen automáticamente (UNION); `--groupby` permite agrupar el resultado combinado, con un parser propio que:
  - Solo soporta `SELECT` simples (no `SELECT DISTINCT/TOP/ALL`, no subconsultas en el `SELECT`).
  - Reescribe la consulta como `SELECT <cols> FROM (SELECT <inner_cols> FROM <from>) t GROUP BY <cols>`, reconociendo agregaciones `MAX/MIN/SUM/AVG/COUNT` (excepto `COUNT(*)`, no soportado todavía).
  - Valida que las columnas de `--groupby` sean nombres simples separados por coma.

## 7. Módulo de exportación (`s50exportador_resultados.py`)

Clase `ExportadorResultados(directorio_salida="resultados")`. Método principal `exportar(datos, formato, nombre_archivo, plantilla, comprimir, abrir_archivo)`.

Formatos soportados (clave `formato` case-insensitive):
- **txt**: tabulado con anchos de columna alineados; si se indica `--plantilla` y el archivo no existe, se genera automáticamente una plantilla base con placeholders `{CAMPO}` en mayúsculas y se avisa al usuario; si existe, se aplica registro por registro (soporta placeholders `{NUMERO}`, `{FECHA}` y `{CAMPO}` por cada clave del diccionario).
- **csv**: `utf-8-sig` (BOM, compatibilidad Excel), vía `csv.DictWriter`.
- **json**: incluye `metadatos` (fecha de generación, total de registros, campos) + `datos`; `indent=2`, `ensure_ascii=False`.
- **xml**: estructura jerárquica `<resultados><metadatos>...</metadatos><datos><registro id="N">...</registro></datos></resultados>`.
- **excel / xlsx**: vía `openpyxl` (fallback automático a CSV si `openpyxl` no está disponible). Genera hoja "Datos" + hoja "Metadatos" (fecha, total registros, columnas). Valores problemáticos (p. ej. no serializables) se normalizan a texto; `datetime` se convierte a ISO.

Post-procesado:
- `--zip`: comprime el archivo resultante en `.zip` (`zipfile.ZIP_DEFLATED`) y elimina el original.
- `abrir_archivo=True` (usado siempre desde `proceso.imprimir_diccionarios`): abre el archivo generado con la aplicación predeterminada — `.csv`/`.json`/`.xml` con Notepad, `.xlsx`/`.xls` intentando `start excel`, resto con Notepad (vía `subprocess.Popen`).
- Utilidad adicional `limpiar_resultados_antiguos(dias=7)`: borra archivos de `resultados/` más antiguos que N días (no está expuesta como comando CLI actualmente).
- Función de conveniencia `exportar_resultados(datos, formato, nombre_archivo, **kwargs)` para uso programático fuera del CLI.

## 8. Core de negocio (`s50proceso.py` — clase `proceso`)

Responsabilidades principales:
- **Licencia y ayuda contextual**: `x11()` de `libwertyconfig`, periodo de gracia de 7 días, apertura automática de página de ayuda en demo/licencia fallida.
- **Resolución de contexto** (`_resolver_contexto_consulta`): normaliza grupo de comunes (acepta número o `COMUxxxx`), resuelve years disponibles y construye la query final vía `api.build_query`.
- **Validación de solo lectura** (`_es_sql_lectura_permitido`): parser manual tokenizando comentarios (`--`, `/* */`), strings (comillas simples con escape `''`), profundidad de paréntesis y separadores `;`; valida CTEs `WITH` que terminan en `SELECT`.
- **Traducción a sintaxis SAGE50** (`_sql_en_formato_sage50`): regex para mostrar el SQL equivalente en notación SAGE50 (para `--sage50`).
- **GROUP BY sobre unión de years** (`_construir_query_groupby` y helpers de parseo SQL): reescribe queries `SELECT` simples para permitir `--groupby` tras unir varios ejercicios.
- **Info de conexión** (`info()`): muestra configuración activa, comunes/nombre/letra, years, versión del SQL Server.
- **Ejecución de SQL** (`sql()`): valida, resuelve, ejecuta con `api.execute_query(commit=False)`, mide tiempo, imprime SQL final.
- **Exportación** (`sql2doc()` → `imprimir_diccionarios()`): valida, resuelve, ejecuta con `api.sql_to_list(as_dict=True)`, exporta vía `ExportadorResultados`.
- **Reset de logs** (`reset_log()`): trunca `log_analisis` y `log_error` en `EUROWINSYS`.
- **Credenciales CRM** (`_obtener_credenciales_crm`): consulta `PRIVATEKEY`/`PUBLICKEY` desde `"FMCRM0{letracomu}"."dbo"."credenciales"`, con detección de "tabla/base inexistente" vs errores reales (guarda `crm_status`: `unknown`/`available`/`unavailable`/`error` y `crm_error`). No está expuesta directamente como comando CLI (uso interno/soporte).

## 9. Scripting extendido (`s50script.py`) — helpers inyectados en `run`

Cuando se usa `s50info run`, además del objeto `proceso`, se inyectan en `builtins` y en el propio `proceso` los siguientes helpers, pensados para ejemplos de tipo "BI ligero":

- **`BI_QUERIES`**: diccionario de consultas SQL predefinidas de ejemplo/reutilizables (dataclass `BIQuery`: `sql`, `titulo`, `descripcion`, `sqlyear`, `grupo_comunes`, `groupby`, `fast_build`). Incluye consultas de negocio reales de ejemplo:
  - `DetalleCargaCamion` (carga de reparto por cliente, etiquetas de envío)
  - `DeudaPorVendedor` (deuda pendiente y % sobre el total)
  - `CuotasClienteConcepto` (cuotas por cliente/concepto con meses de cobro)
  - `Ventas_Dto_Cliente_Articulo` (ventas con descuento medio ponderado por familia/artículo/cliente)
  - `Carga_Reparto_por_cliente`
  - `Rentabilidad_albaran_lote` (rentabilidad detallada por albarán y lote, con prorrateo de coste por peso/unidades)
  - `Ventas_Vendores_por_ranking` (ranking de ventas por vendedor y ejercicio, con `DENSE_RANK`)
  - `Deuda_plazo_medio_vendedor_mes` (deuda pendiente y plazo medio de cobro por vendedor/mes)
- **`query_to_dict(sql, proc=None, sqlyear="+", grupo_comunes=None, groupby=None, fast_build=False)`**: ejecuta una query de lectura y devuelve `list[dict]`. Soporta un modo `fast_build` que evita el camino normal de `build_query` y arma la query directamente vía `api._prepare_template` + `_replace_year_placeholder`, uniendo con `UNION ALL` si hay múltiples years.
- **`samplebi(nombre, proc=None, sqlyear=None, grupo_comunes=None, groupby=None, fast_build=False)`**: devuelve datos de una query predefinida por nombre (case-insensitive), usando los defaults de `BIQuery` salvo que se sobreescriban.
- **`samples_disponibles(nombres=None)`**: lista nombre/título/descripción de los samples sin exponer el SQL.
- **`exportar_samples(nombres, proc=None)`**: obtiene datos de varios samples BI, continuando ante errores individuales; retorna metadata + `datos`/`registros`/`ok`/`error` por cada uno (no exporta a archivo, deja esa decisión al script llamador).
- **`seleccionar_samples(nombres=None)`**: selector interactivo por consola (usa `msvcrt`, solo Windows) para elegir qué samples generar — controles: flechas arriba/abajo, espacio (marcar), T (todos), N (ninguno), Enter (confirmar), Esc (cancelar).

Estos helpers están pensados para que los scripts de la carpeta `script/` (ejecutados vía `s50info run ./script`) puedan generar reportes BI rápidos sin reescribir SQL desde cero, también accesibles como métodos de `proceso` (`proceso.query_to_dict(...)`, `proceso.samplebi(...)`, etc.).

## 10. Configuración (`config.ini`)

```ini
[API]
direccion_servidor = <instancia SQL Server>   ; ej. CUBA\SQLSAGE50
nombre_usuario = <usuario>
password = <contraseña>
driver_servidor = SQL Server Native Client 11.0
terminal = C:\Sage50\Sage50Term
comunes = <código de comunes>                 ; ej. 4 o COMU0004
autenticacion_sql = True/False

[CONFIG_SAGE50]
empresa = <empresa SAGE50>
usuario = <usuario SAGE50>
password = <contraseña SAGE50>
```

- Variables sensibles pueden sobreescribirse vía `.env` (`python-dotenv`).
- `.env` con `DEBUG=True/Si/1` activa logging detallado (`pysage50e.sage_debug_config`).
- `config.ini` debe excluirse de git (contiene credenciales).

## 11. Dependencias principales

| Paquete | Propósito |
|---|---|
| `typer` | Framework CLI |
| `rich` | Salida enriquecida por consola |
| `pyodbc` | Conexión ODBC a SQL Server |
| `pysage50e` | API oficial SAGE50 (conexión, queries, resolución de years/comunes) |
| `polars` | Procesamiento de datos (opcional, con check de CPU deshabilitable) |
| `openpyxl` | Generación de Excel |
| `python-docx` | Generación/merge de documentos Word (uso futuro, ver roadmap) |
| `pythonnet` | Interop .NET |
| `cryptography` | Cifrado/gestión de claves (licencia) |
| `httpx` | Cliente HTTP (actualizaciones) |
| `python-dotenv` | Variables de entorno `.env` |
| `sqlparse` | Parseo/formateo SQL |
| `psutil` | Utilidades de sistema |
| `pytest` | Testing |
| `pyinstaller` | Empaquetado a ejecutable |
| `cython` | Compilación de extensiones C (`c/Capi.py`) |

Dependencias externas no-Python: **SQL Server Native Client 11.0** (driver ODBC) e instancia SQL Server con bases `EUROWINSYS` + `COMUxxxx` (y opcionalmente `FMCRM0xx` para CRM).

## 12. Build y release (gestión de proyecto, no funcionalidad de usuario final)

- Build principal: `c/build_exe.py`; metadata en `c/product.json`.
- Modos de build:
  - **full/zip**: compila Cython → PyInstaller (onedir) → copia `config.ini`/`licencia.lic`/plantillas → genera ZIP en `c/RELEASE/` protegido con contraseña, sincroniza `c/RELEASE/release.json` (versión, nombre de ZIP, `type=full` si corresponde) → genera `.last_build` al final del flujo exitoso.
  - **pyd**: compila con `pydobj`, copia solo `.pyd` modificados a `c/RELEASE/_internal` (staging acumulativo desde el último `full`); no genera ZIP ni actualiza `release.json` ni `.last_build`; se puede limpiar `_internal` antes de copiar.
- Publicación: `c/RELEASE/release.py` firma el manifest (`pyupdategit build-manifest`), luego ejecuta `mkdocs gh-deploy --force` desde `docs_repo` (limpiando `docs/es` y recreando el directorio de updates antes, borrando `site/` después).
- Scripts alternativos: `@hacer.ps1` (recomendado), `hacer.bat` (simplificado).

## 13. Testing

- `test_cli.py`, `test_proceso.py`, `test_exportador_resultados.py`, `test_exportador_config.py`.
- Ejecución: `pytest` desde la raíz.
- Convención de entornos: `.venv` en Windows (no tocar desde Linux/WSL); `.venvlinux` para agentes Linux/WSL, forzando `UV_PROJECT_ENVIRONMENT=.venvlinux`. Gestión de dependencias exclusivamente con `uv` (no `pip` directo).

## 14. No objetivos / límites explícitos

- No sustituye a SSMS para administración completa de SQL Server.
- No gestiona usuarios, permisos ni backups de base de datos.
- No es una herramienta ETL (no transforma/migra esquemas).
- No tiene interfaz web ni API REST.
- No es multiplataforma (solo Windows).
- Solo permite SQL de lectura (`SELECT`/`WITH`); rechaza cualquier escritura o múltiples sentencias.

## 15. Roadmap (propuestas, no implementadas aún)

- Logging estructurado con archivo rotativo.
- Generación de documentos Word con merge de plantillas desde SQL (ya hay dependencia `python-docx` preparada).
- Soporte de múltiples perfiles de conexión.
- Salida en formato Markdown.
- Paginación de resultados en consola.
- Modo interactivo (REPL SQL).
- Soporte `COUNT(*)` en `--groupby` (actualmente no soportado).

## 16. Glosario

| Término | Definición |
|---|---|
| **Comunes** | Base de datos de configuración compartida en SAGE50 (código numérico, ej. `COMU0004`); todas las empresas comparten ciertas tablas. |
| **Letra de comunes** | Sufijo alfabético que identifica la instalación (ej. `A`); se usa para construir nombres de bases como `FMCRM0A`. |
| **Años/years** | Ejercicios fiscales abiertos; una empresa puede tener varios simultáneos. |
| **EUROWINSYS** | Base de sistema SAGE50 (config global, logs, estructura). |
| **FMCRM0xx** | Base del módulo CRM; contiene credenciales API en `dbo.credenciales`. |
| **pysage50e** | Librería que encapsula la API nativa de SAGE50 (conexión, queries, negocio). |
| **apiSAGE50** | Clase principal de `pysage50e`. |
| **Carencia** | Periodo de gracia de 7 días desde la creación de `config.ini` en el que no se solicita formulario de contacto aunque la licencia esté en demo/no válida. |
