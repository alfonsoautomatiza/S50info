# PRD — S50Info: Herramienta de Administración para Bases de Datos SAGE50

| Campo | Valor |
|-------|-------|
| **Producto** | S50Info (`tool-sage50`) |
| **Versión** | 0.1.0 |
| **Estado** | En desarrollo |
| **Autor** | ALCA TIC, S.L. |
| **Fecha** | Marzo 2026 |
| **Stack** | Python 3.13+ / Typer / Rich / PyInstaller |

---

## 1. Resumen Ejecutivo

S50Info es una herramienta de línea de comandos (CLI) diseñada para administradores y desarrolladores que operan instalaciones de SAGE50 ERP. Centraliza en un único ejecutable las operaciones más frecuentes sobre las bases de datos SQL Server subyacentes: ejecución de consultas SQL, exportación multiformato de resultados, recuperación de credenciales, ejecución de scripts de mantenimiento, y gestión de logs del sistema.

El producto se distribuye como un ejecutable Windows autónomo (PyInstaller) que no requiere instalación de Python ni dependencias en la máquina del usuario final. Toda la configuración de conexión se centraliza en un archivo `config.ini` que acompaña al ejecutable.

---

## 2. Problema

Los administradores de SAGE50 enfrentan tareas repetitivas y fragmentadas en su día a día:

1. **Consultas SQL dispersas**: necesitan SQL Server Management Studio (SSMS) para consultas puntuales, lo cual es pesado para una simple verificación.
2. **Exportación manual**: generar informes Excel/CSV desde SSMS requiere múltiples pasos manuales (ejecutar, copiar, pegar, limpiar).
3. **Scripts desconectados**: los scripts de mantenimiento se ejecutan fuera del contexto SAGE50, obligando a replicar la lógica de conexión en cada uno.
4. **Credenciales opacas**: recuperar la clave SQL desde la licencia SAGE50 es un proceso manual y propenso a errores.
5. **Distribución compleja**: compartir herramientas Python entre equipos requiere instalar intérpretes, dependencias y configurar entornos virtuales.

S50Info resuelve estos cinco puntos con una sola herramienta portable.

---

## 3. Público Objetivo

| Perfil | Descripción | Uso típico |
|--------|-------------|------------|
| **Administrador de sistemas** | Responsable de mantener instancias SAGE50 | Reset de logs, verificación de conexión, copia de credenciales |
| **Desarrollador/Integrador** | Crea scripts contra datos SAGE50 | Ejecución de SQL, exportación para otros sistemas |
| **Consultor ERP** | Realiza auditorías y migraciones | Exportación masiva de datos, consultas ad-hoc |
| **Contable/Financiero (avanzado)** | Necesita reportes rápidos sin SSMS | Exportación a Excel desde consultas predefinidas |

**Requisito previo para todos**: acceso a una instancia SAGE50 con credenciales válidas de SQL Server y el driver ODBC correspondiente.

---

## 4. Objetivos del Producto

### 4.1 Objetivos principales

- **OBJ-1**: Permitir ejecutar cualquier consulta SQL contra la base de datos del comunes activo sin necesidad de SSMS.
- **OBJ-2**: Exportar resultados de consultas a 6 formatos: TXT (tabulado), TXT con plantilla, CSV, JSON, XML y Excel (.xlsx).
- **OBJ-3**: Ejecutar scripts Python externos con acceso completo al contexto SAGE50 (objeto `proceso` pre-inyectado).
- **OBJ-4**: Distribuir el producto como una herramienta puramente de consola para operaciones técnicas sobre SAGE50.
- **OBJ-5**: Distribuir el producto como un ejecutable Windows autónomo (sin dependencias externas).

### 4.2 No objetivos (Out of scope)

- No es un sustituto de SSMS para administración completa de SQL Server.
- No gestiona usuarios, permisos, ni backups de base de datos.
- No es un ETL; no transforma ni migra datos entre esquemas.
- No tiene interfaz web ni API REST.
- No es multiplataforma (target: Windows exclusivamente).

---

## 5. Requisitos Funcionales

### RF-01 — Conexión a SAGE50

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-01.1 | Conectar a la instancia SQL Server configurada en `config.ini` al iniciar | Crítica |
| RF-01.2 | Detectar y reportar errores de conexión (servidor caído, credenciales inválidas, driver ausente) | Crítica |
| RF-01.3 | Cargar el contexto de empresa/comunes activa (código de comunes, nombre, letra, años fiscales) | Crítica |
| RF-01.4 | Verificar licencia mediante `libwertyconfig` (carencia o licencia válida) | Alta |

### RF-02 — Ejecución de consultas SQL

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-02.1 | Ejecutar consultas SQL de lectura contra la base del comunes activo (flag `--sql` / `-s`) | Crítica |
| RF-02.2 | Soportar la sintaxis extendida de SAGE50 (`GESTION!CLIENTES`, `*` como comodín de años) | Crítica |
| RF-02.3 | Rechazar consultas SQL de escritura y permitir solo consultas de lectura (`SELECT`/`WITH`) | Alta |
| RF-02.4 | Mostrar resultado por consola con formato enriquecido (Rich) | Media |

### RF-03 — Exportación de resultados

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-03.1 | Exportar resultados de consultas a formato TXT tabulado | Crítica |
| RF-03.2 | Exportar a CSV (codificación UTF-8 BOM para compatibilidad Excel) | Alta |
| RF-03.3 | Exportar a JSON con metadatos (fecha, total registros, campos) | Alta |
| RF-03.4 | Exportar a XML con estructura jerárquica y metadatos | Media |
| RF-03.5 | Exportar a Excel (.xlsx) con hoja de datos y hoja de metadatos | Alta |
| RF-03.6 | Aplicar plantillas personalizadas para formato TXT (sustitución de marcadores `{CAMPO}`) | Media |
| RF-03.7 | Comprimir automáticamente el resultado en ZIP (flag `--zip` / `-z`) | Media |
| RF-03.8 | Abrir automáticamente el archivo generado con la aplicación predeterminada del sistema | Baja |

### RF-04 — Scripts Python externos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-04.1 | Ejecutar un archivo Python individual con acceso al objeto `proceso` inyectado (flag `--exe` / `-e`) | Alta |
| RF-04.2 | Ejecutar todos los archivos `.py` de un directorio en orden alfabético | Alta |
| RF-04.3 | Reportar errores por script sin interrumpir la ejecución de los restantes | Alta |
| RF-04.4 | Validar existencia de la ruta del script antes de ejecutar | Alta |
| RF-04.5 | Rechazar archivos que no sean `.py` | Baja |

### RF-05 — Gestión de credenciales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-05.1 | Consultar credenciales CRM (PRIVATEKEY, PUBLICKEY) desde la base `FMCRM0xx` cuando aplique al flujo técnico | Media |

### RF-06 — Mantenimiento

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-06.1 | Truncar tablas de log del sistema (`log_analisis`, `log_error` en EUROWINSYS) con flag `--reset` / `-r` | Alta |
| RF-06.2 | Mostrar información de la conexión activa (servidor, comunes, versión SQL, años) en modo por defecto | Media |

---

## 6. Requisitos No Funcionales

| ID | Categoría | Requisito | Métrica/Target |
|----|-----------|-----------|----------------|
| RNF-01 | Performance | Tiempo de inicio (conexión incluida) | < 5 segundos en red local |
| RNF-02 | Performance | Exportación de hasta 10,000 filas a Excel | < 10 segundos |
| RNF-03 | Portabilidad | Ejecutable autónomo sin dependencias externas | Funciona en Windows 10+ limpio |
| RNF-04 | Usabilidad | CLI auto-documentada (Typer help integrado) | `s50info --help` muestra todos los comandos |
| RNF-05 | Mantenibilidad | Código modular con separación de responsabilidades | Módulos: CLI, proceso, exportador |
| RNF-06 | Seguridad | Credenciales en `config.ini` excluidas de git | Archivo en `.gitignore` |
| RNF-08 | Distribución | Build reproducible via script PowerShell (`@hacer.ps1`) | Un comando genera la distribución ZIP |
| RNF-09 | Compatibilidad | Driver ODBC SQL Server Native Client 11.0 | Configurable en `config.ini` |

---

## 7. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    s50info.exe                          │
│  ┌───────────┐  ┌────────────┐  ┌──────────────┐       │
│  │ s50info.py│  │ proceso.py │  │ exportador   │       │
│  │  (CLI     │──│  (Core     │──│ _resultados  │       │
│  │  Typer)   │  │  Business) │  │ _config      │       │
│  └───────────┘  └─────┬──────┘  └──────────────┘       │
│                       │                                │
│           ┌───────────┼───────────┐                    │
│           ▼           ▼                                │
│  ┌─────────────┐ ┌──────────┐ ┌──────────────┐        │
│  │ pysage50e   │ │libwerty  │ │ exportador   │        │
│  │ (API SAGE50)│ │config    │ │ _resultados  │        │
│  └──────┬──────┘ └──────────┘ │ _config      │        │
│         │                     └──────────────┘        │
└─────────┼─────────────────────────────────────────────┘
          │ pyodbc / ODBC
          ▼
┌─────────────────────────┐
│   SQL Server            │
│  ┌──────────────────┐   │
│  │ EUROWINSYS       │   │
│  │ COMUxxxx (datos) │   │
│  │ FMCRM0xx (CRM)   │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

### Módulos principales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| **CLI** | `s50info.py` | Parseo de argumentos (Typer), orquestación de comandos |
| **Core** | `proceso.py` | Lógica de negocio: SQL, exportación, credenciales, info, reset |
| **Exportador** | `exportador_resultados.py` | Motor de exportación multiformato (TXT, CSV, JSON, XML, XLSX) |
| **Config Export** | `exportador_config.py` | Configuración dataclass del exportador (delimitadores, encoding, etc.) |
| **Cython** | `c/Capi.py` | Extensiones compiladas Cython (build_ext) |
| **Build** | `@hacer.ps1`, `hacer.bat` | Scripts de build (Cython + PyInstaller + distribución ZIP) |

---

## 8. Flujo de Datos Principal

```
Usuario ejecuta comando CLI
        │
        ▼
  ┌─ Subcomando recibido? ────────────────────────────────┐
  │                                                        │
  ├─ info ───────► proceso.info() ───────► consola         │
  ├─ sql ────────► proceso.sql() ────────► consola         │
  ├─ export ─────► proceso.sql2doc() ────► exportador      │
  ├─ run ────────► runpy.run_path(script) ─► consola       │
  ├─ reset ──────► proceso.reset_log() ───► consola        │
  └─ (ninguno) ──► proceso.info() ────────► consola        │
```

---

## 9. Configuración

### config.ini

```ini
[API]
direccion_servidor = <instancia SQL Server>
nombre_usuario = <usuario>
password = <contraseña>
driver_servidor = SQL Server Native Client 11.0
terminal = c:\Sage50\Sage50Term
comunes = <código de comunes>
autenticacion_sql = False

[CONFIG_SAGE50]
empresa = <empresa SAGE50>
usuario = <usuario SAGE50>
password = <contraseña SAGE50>
```

### Variables de entorno (`.env`)

- Variables sensibles pueden sobreescribirse mediante archivo `.env` (soporte `python-dotenv`).

---

## 10. Interfaz de Usuario

### CLI (principal)

```
s50info [OPCIONES] [COMANDO]

Comandos:
  info      Mostrar informacion de la conexion activa
  sql       Ejecutar una consulta SQL de lectura
  export    Ejecutar una consulta SQL de lectura y exportarla
  run       Ejecutar un script Python o todos los scripts de un directorio
  reset     Truncar logs de SAGE50

Opciones globales:
  --pausa / --no-pausa       Pausa al final de la salida informativa
  --grupo-comunes TEXT       Grupo de comunes a usar; si no se indica, se toma de config.ini

Opciones de consulta/exportacion:
  --sqlyear, -a TEXT         Especificacion de years: + | * | @ | 2025JX | 2024JX,2025JX
  --grupo-comunes, -c TEXT   Grupo de comunes a usar; si no se indica, se toma de config.ini
  --groupby, -b TEXT         Agrupar el resultado final tras unir varios years
  --sage50                   Mostrar la consulta equivalente en sintaxis SAGE50
  -f, --formato TEXT         Formato de exportacion: txt|csv|json|xml|xlsx
  -o, --output TEXT          Nombre base del archivo de salida
  -t, --plantilla TEXT       Ruta a plantilla TXT personalizada
  -z, --zip                  Comprimir resultado en ZIP
```

### Ejemplos

```bash
s50info
s50info info --grupo-comunes 4
s50info sql "select * from #clientes" --sqlyear @
s50info sql "select CODIGO, MAX(NOMBRE) from #clientes" -a @ -b CODIGO
s50info sql "select * from #clientes" --sage50
s50info export "select * from #clientes" --sqlyear "2024JX,2025JX" --formato json
s50info run .\scripts
s50info reset
```

---

## 11. Distribución y Build

### Pipeline de build

1. **Cython**: Compilar extensiones C en `c/Capi.py` → `build_ext --inplace`
2. **PyInstaller**: Empaquetar como carpeta (modo `onedir`) según `s50info.spec`
3. **Copia**: Mover `config.ini`, `licencia.lic`, `plantilla.docx` y carpetas necesarias al directorio `exe/`
4. **ZIP**: Crear archivo ZIP protegido con contraseña para distribución

### Comandos

```bash
# Build completo (recomendado)
.\@hacer.ps1

# Build simplificado
hacer.bat
```

### Archivos de distribución

| Archivo | Descripción |
|---------|-------------|
| `s50info/` | Carpeta del ejecutable (PyInstaller onedir) |
| `config.ini` | Configuración de conexión |
| `licencia.lic` | Licencia de la herramienta |
| `plantilla.docx` | Plantilla Word para generación de documentos |

---

## 12. Testing

| Archivo de test | Módulo testeado |
|-----------------|-----------------|
| `test_cli.py` | CLI (Typer commands) |
| `test_proceso.py` | Lógica de negocio (proceso) |
| `test_exportador_resultados.py` | Exportación multiformato |
| `test_exportador_config.py` | Configuración del exportador |

Ejecución: `pytest` desde la raíz del proyecto.

---

## 13. Dependencias

### Dependencias directas

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `typer` | >=0.21.1 | Framework CLI |
| `rich` | (implícito) | Salida enriquecida por consola |
| `pyodbc` | >=5.3.0 | Conexión ODBC a SQL Server |
| `pysage50e` | >=0.1.1 | API oficial SAGE50 para Python |
| `polars` | >=1.37.1 | Procesamiento de datos para exportación |
| `openpyxl` | >=3.1.5 | Generación de archivos Excel |
| `python-docx` | >=1.2.0 | Generación de documentos Word (merge de plantillas) |
| `pythonnet` | >=3.0.5 | Interoperabilidad .NET |
| `cryptography` | >=46.0.4 | Cifrado y gestión de claves |
| `httpx` | >=0.28.1 | Cliente HTTP (actualizaciones) |
| `python-dotenv` | >=1.2.1 | Variables de entorno desde `.env` |
| `sqlparse` | >=0.5.5 | Parseo y formateo SQL |
| `psutil` | >=7.2.2 | Utilidades de sistema |
| `pytest` | >=9.0.2 | Framework de testing |
| `pyinstaller` | >=6.18.0 | Empaquetado a ejecutable |
| `cython` | >=3.2.4 | Compilación de extensiones C |

### Dependencias externas (no Python)

- **SQL Server Native Client 11.0** — Driver ODBC instalado en el sistema
- **Instancia SQL Server** — Con base de datos EUROWINSYS y bases de empresa

---

## 14. Normas de build y release

### 14.1 Build completo / ZIP

- `c/build_exe.py` es el script de build principal.
- En modo `zip`, debe generar el ZIP dentro de `c/RELEASE/`.
- En modo `zip`, debe sincronizar `c/RELEASE/release.json` con:
  - versión de `c/product.json`,
  - nombre del ZIP generado,
  - `type = "full"` cuando corresponda a una release base de major.
- El ZIP generado debe ser el artefacto que luego consume `c/RELEASE/release.py`.

### 14.2 Modo `pyd`

El modo `pyd` existe para preparar binarios compilados modificados entre versiones completas.

Normas obligatorias:

- El modo `pyd` compila con `pydobj`.
- Copia únicamente ficheros `.pyd`.
- El destino de staging es:

  ```text
  c/RELEASE/_internal
  ```

- `c/RELEASE/_internal` es una carpeta de staging acumulativo de `.pyd` modificados desde la última versión `full`.
- No representa por sí misma una release partial completa.
- El modo `pyd` **no** debe generar ZIP automáticamente.
- El modo `pyd` **no** debe actualizar `c/RELEASE/release.json`.
- El empaquetado/publicación posterior se ejecuta manualmente por el usuario en el flujo que corresponda.
- Es correcto limpiar `c/RELEASE/_internal` antes de copiar los `.pyd` modificados, porque esa carpeta solo representa el staging actual de binarios compilados.
- El modo `pyd` debe usar `.last_build` como baseline de la última versión `full`.
- El modo `pyd` no debe actualizar `.last_build`; así puede seguir acumulando todos los `.pyd` modificados hasta la siguiente versión completa.
- Si no existe `.last_build`, puede copiar todos los `.pyd` para evitar un staging vacío.
- Este flujo se ejecuta siempre en Windows; no es requisito soportar diferencias de sensibilidad a mayúsculas/minúsculas de WSL/Linux para extensiones `.pyd`.
- En los modos `full`/`zip`, `.last_build` debe generarse al final del proceso completo, únicamente después de que PyInstaller, copias extra, ocultación de `_internal`, creación del ZIP y sincronización de `release.json` hayan terminado correctamente.

### 14.3 Publicación

- La publicación final se realiza con `c/RELEASE/release.py`.
- `release.py` firma siempre el manifest con `pyupdategit build-manifest`.
- Después de crear/firmar el manifest, debe ejecutar `mkdocs gh-deploy --force` desde `docs_repo`.
- Antes del deploy, limpia `docs/es` y recrea `<docs_repo>/<updates_dir>`.
- Después del deploy, elimina `site/`.

---

## 15. Roadmap

### Versión actual (0.1.0)

- [x] CLI con Typer
- [x] Conexión a SAGE50 vía `pysage50e`
- [x] Ejecución de consultas SQL
- [x] Exportación multiformato (TXT, CSV, JSON, XML, XLSX)
- [x] Plantillas personalizadas TXT
- [x] Compresión ZIP
- [x] Ejecución de scripts Python externos
- [x] Herramienta puramente CLI
- [x] Reset de logs
- [x] Build con PyInstaller
- [x] Tests unitarios

### Próximas versiones (propuestas)

- [ ] Logging estructurado con archivo rotativo
- [ ] Generación de documentos Word con merge de plantillas desde SQL
- [ ] Soporte para múltiples configuraciones de conexión (perfiles)
- [ ] Salida en formato Markdown
- [ ] Paginación de resultados en consola
- [ ] Modo interactivo (REPL SQL)

---

## 16. Glosario

| Término | Definición |
|---------|------------|
| **Comunes** | Base de datos de configuración compartida en SAGE50, identificada por un código numérico (ej: `COMU0004`). Todas las empresas comparten ciertas tablas en el comunes. |
| **Letra de comunes** | Sufijo alfabético que identifica la instalación SAGE50 (ej: `A`). Se usa para construir nombres de bases como `FMCRM0A`. |
| **Años** | Ejercicios fiscales abiertos. Una empresa puede tener múltiples años activos simultáneamente. |
| **EUROWINSYS** | Base de datos del sistema SAGE50 que contiene configuración global, logs y tablas de estructura. |
| **FMCRM0xx** | Base de datos del módulo CRM de SAGE50, donde `xx` es la letra de comunes. Almacena credenciales API en la tabla `dbo.credenciales`. |
| **pysage50e** | Librería Python que encapsula la API nativa de SAGE50, proporcionando conexión, ejecución de consultas y funciones de negocio. |
| **apiSAGE50** | Clase principal de `pysage50e` que gestiona la conexión y operaciones contra la base de datos SAGE50. |
