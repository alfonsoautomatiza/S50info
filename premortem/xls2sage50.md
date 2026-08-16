# xls2sage50 — Resumen funcional completo

## 1. Propósito

**xls2sage50** es una herramienta (aplicación de escritorio/web + CLI) que conecta archivos **Excel/CSV** con el software contable **SAGE50**, eliminando la carga manual de registros. Permite:

- Importar datos nuevos (artículos, clientes, proveedores, presupuestos, etc.) desde Excel/CSV hacia SAGE50.
- Hacer actualizaciones masivas sobre datos **ya existentes** en SAGE50 (módulo "Proceso Masivo").

Autor: AMG (c) 2026. Requiere licencia válida (`licencia.lic`); sin ella la app no funciona.

## 2. Formatos de entrada / salida

**Entrada:**
- Excel (`.xlsx`, `.xls`) — lectura vía Polars
- CSV

**Salida:**
- Importación directa a SAGE50 vía API .NET (`apiSage50net` + `pythonnet`)
- Archivos CSV compatibles con el asistente de importación nativo de SAGE50 (para quien no tenga la API habilitada)
- Excel de errores (post-importación, para corrección)
- Reportes de diagnóstico de API (JSON/TXT)
- Excel de trabajo para Proceso Masivo (con fórmulas, colores, columnas ocultas de backup)

## 3. Modos de ejecución

| Modo | Descripción | Invocación |
|---|---|---|
| Desktop | Ventana nativa Flet (predeterminado en EXE) | `FLET_VIEW_MODE=DESKTOP` |
| Web | Navegador en `http://localhost:5900/raiz/` | `FLET_VIEW_MODE=WEB` |
| CLI | Línea de comandos (Typer) | `python xls2sage50.py <cmd>` (código fuente) / `xls2sage50.exe <cmd>` (empaquetado). No hay script instalado `xls2sage50` (pyproject sin `[project.scripts]`) |

## 4. Comandos CLI (Typer, `codigo/cli.py`)

- **`run <plantilla>`** — Ejecuta una plantilla `.PREDEFINIDO`. El modo (CSV o API) se detecta automáticamente según si la plantilla contiene `tablasage50`. Valida antes de ejecutar. Opciones: `--excel/-e` (sobrescribe Excel), `--output/-o` (CSV salida), `--verbose/-v`.
- **`validate <plantilla>`** — Valida estructura de una plantilla (y opcionalmente conexión API con `--check-api`). Si no se indica plantilla, la pide interactivamente y lista las disponibles.
- **`api-check`** — Prueba de acceso/conexión a la API SAGE50 (módulo disponible, licencia, config, conexión efectiva). Opciones: `--export/-o` (reporte), `--format/-f` (json/txt), `--probe/--no-probe`.
- **`list`** — Lista plantillas disponibles en tabla enriquecida (Rich): nombre, tipo (API/CSV), entidad, Excel, hoja, modo de importación. Filtro `--type/-t csv|api`.
- **`--version`** — Muestra versión de la app.

## 5. Funcionalidades principales

### 5.1 Importación vía API SAGE50
- Conexión mediante API .NET (`apiSage50net` + `pythonnet`)
- Importación directa sin paso intermedio
- Procesamiento asíncrono por lotes (chunks, default 25 registros, configurable) con reintentos (3 intentos, delay 1s, timeout 30s)
- Modos: solo nuevos / actualizar si existe / crear y actualizar
- Validación previa con modelos Pydantic
- Generación de Excel de errores
- Posibilidad de detener el proceso manualmente

### 5.2 Generación de CSV
- Exporta CSV compatible con el asistente de importación de SAGE50
- Formato configurable según entidad destino
- Pensado para usuarios sin API habilitada

### 5.3 Sistema de plantillas (`.PREDEFINIDO`)
- Guarda mapeos campo-a-campo columna Excel ↔ campo SAGE50
- Valores constantes configurables por plantilla
- Auto-mapeo por similitud de nombres normalizados
- Para documentos multilínea (presupuestos): selección manual del campo índice, con propuesta automática por análisis de nombres y repetición de valores consecutivos
- Reutilizables entre sesiones, compartibles

### 5.4 Validación de datos
- Verificación de tipos, formatos y obligatoriedad antes de enviar a SAGE50 (Pydantic)

### 5.5 Entidades soportadas
Artículos, Clientes, Proveedores, Familias, Subfamilias, Formas de pago, Agencias, Presupuestos de venta, Presupuestos de compra, y cualquier entidad expuesta por la API de SAGE50.

### 5.6 Proceso Masivo (SQLX) — módulo `codigo/masivo/`
Actualizaciones masivas sobre datos **ya existentes** en SAGE50 (migración conceptual de la herramienta legacy `sage2xls`), a diferencia de 5.1/5.2 que cargan datos nuevos.

- Definición del proceso: archivos `.sqlx` (formato `configparser`, sección `[DB]`) con tabla (`bdupdate`), columnas clave (`filtro`), columnas a actualizar (`camposupdate`), consulta opcional (`persql`), año/base (`year`).
- **Exportar**: genera un Excel por proceso en `procesos/masivo/pending/` con nombre único por timestamp. Incluye:
  - Columnas de resumen en vivo `DATOS A CAMBIAR` / `FILTRO` con fórmulas (recalculan solas al editar)
  - Columnas coloreadas por rol: clave = azul, editable = amarillo, referencia = gris
  - Columna oculta `__orig_key__<clave>` (snapshot inmutable para el WHERE)
  - Columna visible `ORIGINAL_<campo>` por cada campo editable (backup del valor previo)
- **Validar SQL**: genera el `.sql-preview.txt` exacto a ejecutar (mismo artefacto reusado al ejecutar). Celda editable vacía se excluye del `SET` (no pone `NULL`); si toda la fila queda vacía, se omite.
- **Ejecutar**: reutiliza el preview validado; bloquea si el archivo cambió desde la validación. Pide confirmación explícita (modal, advierte irreversibilidad, pide backup). Política **todo o nada**: si falla cualquier fila, rollback completo del lote y el workbook no pasa a `processed/`.
- **Eliminar pendiente**: borrado permanente con confirmación.
- Acceso desde tab "Importar › ¿Cómo importar?" (tercera opción junto a API/CSV) y desde pestaña propia en la navegación.
- Interfaz en castellano.

## 6. Interfaz de usuario

Navegación por tabs:

| Tab | Función |
|---|---|
| Importar | Selección de archivo, hoja, entidad, plantilla |
| Proceso API | Mapeo de campos, validación, importación vía API |
| Proceso CSV | Generación y descarga de CSV |
| Proceso Masivo | Actualizaciones masivas SQLX (ver 5.6) |
| Configuración | Parámetros API, tema, valores por defecto |
| Ayuda | Documentación integrada |

## 7. Configuración

**Variables de entorno (`.env`):**
| Variable | Default | Descripción |
|---|---|---|
| `FLET_VIEW_MODE` | `DESKTOP` | `DESKTOP` o `WEB` |
| `FLET_SERVER_PORT` | `5900` | Puerto modo web |
| `FLET_DEBUG` | `false` | Logs detallados |
| `DUMP_API_PAYLOADS` | `false` | Vuelca payloads de importación API a `logs/debug_api/` (git-ignored), enmascarando campos sensibles (NIF, EMAIL, PHONE, PASSWORD, TOKEN, SECRET, KEY) |

**`config.ini`:**
- `[API]` — conexión SAGE50 (URL, empresa, usuario)
- `[THEME]` — tema oscuro/claro
- `[IMPORT_SETTINGS]` — chunk_size, modo por defecto
- `[DEFAULT_VALUES]` — moneda, formato fecha, idioma

## 8. Requisitos técnicos
- Python ≥ 3.13, gestor `uv`
- Windows (API .NET obligatoria, DLL en `C:\Sage50\Sage50Term\Librerias\`)
- SAGE50 instalado con API habilitada (para modo API)
- Licencia válida (`licencia.lic`) + addon API para importación directa

## 9. Arquitectura y dependencias clave

```
xls2sage50.py (entry point)
    └── Xls2Sage50App (Mixin: GuiLayout + FileFlow + ImportWorkflow + Utility)
        ├── ImportTab (codigo/inicial/, mixins UI/eventos/API/plantillas/proceso)
        ├── ProcessTab (mapeo + importación API)
        ├── CsvProcessTab (generación CSV)
        ├── ConfigTab
        └── HelpTab

GUI (Flet) → codigo.inicial.ImportTab → ProcessTab/CsvProcessTab
GUI (Flet) → Presenter → ImportManager → SAGE50Processor → apiSage50net (.NET)
CLI (Typer) → cli_processor → ImportManager / CSV
```

| Dependencia | Rol |
|---|---|
| Flet ≥ 0.84 | UI desktop + web |
| Polars | Procesamiento de datos |
| Pydantic | Validación de modelos |
| pythonnet | Bridge Python↔.NET para API SAGE50 |
| apiSage50net (externa) | API alto nivel SAGE50 |
| pysage50e (externa) | Wrapper pythonnet + SQL |
| Typer | CLI |
| Rich | Salida enriquecida en consola |
| xlsxwriter | Excel con fórmulas/formato (Proceso Masivo) |
| pyodbc | Conexión SQL Server directa (Proceso Masivo) |

## 10. Estado actual (según PRD, 2026-07-24)

**Funcional:** importación API (artículos, clientes, proveedores confirmados), generación CSV, plantillas, auto-mapeo, modos desktop/web/CLI, Proceso Masivo SQLX (exportar/validar/ejecutar/eliminar) verificado contra SAGE50 real.

**Pendiente:** estabilización del pipeline de build (Cython `.py→.pyd` + PyInstaller, bloqueado por sintaxis `X | Y` en ~199 instancias); eliminar fallback legacy `returdicmodelo`; fix `UnicodeEncodeError` con emojis en stdout Windows (cp1252, ya mitigado en CLI con `errors="replace"`).

## 11. Estructura del proyecto (resumen)

```
xls2sage50/
├── xls2sage50.py                  # Entry point
├── codigo/
│   ├── cliente_api_sage50net.py   # Comunicación API SAGE50
│   ├── import_manager.py          # Orquestador importación
│   ├── data_excel_processor.py    # Lectura/parseo Excel (Polars)
│   ├── data_validacion.py         # Validación (Pydantic)
│   ├── template_manager.py        # Gestión de plantillas
│   ├── vista_importa_api.py       # Progreso API async, chunks, retry
│   ├── cli.py                     # CLI Typer
│   ├── cli_processor.py           # Runners CLI (API/CSV/validación)
│   ├── inicial/                   # Tab Importar (mixins)
│   ├── masivo/                    # Proceso Masivo SQLX
│   ├── tab_proceso_mapeo.py       # Tab Mapeo
│   ├── tab_data_csv_process.py    # Tab Proceso CSV
│   ├── tab_config.py              # Tab Configuración
│   ├── gui/                       # MVP: presenter, view, controllers
│   ├── services/                  # entity_loader, company
│   └── ui/                        # state, dialogs, layout
├── c/                              # Scripts de build/release
├── config.ini / .env / pyproject.toml
```

Fuentes revisadas: `README.md`, `PRD.md`, `AGENTS.md`/`CLAUDE.md`, `codigo/cli.py`, estructura de `codigo/masivo/` y `onbordin/`.
