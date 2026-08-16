# Sage50BI — Resumen funcional completo

## 1. Propósito del proyecto

**Sage50BI** es una solución de **Business Intelligence para Sage 50** (ERP contable/comercial), desarrollada por **ALCA TIC, S.L.** (https://pedironline.com). Permite a las PYMEs españolas que usan Sage 50 generar informes SQL, crear cuadros de mando interactivos y automatizar la distribución de esa información, sin depender de un departamento de TI.

- **Público objetivo:** PYMEs españolas usuarias de Sage 50, especialmente sin recursos técnicos internos.
- **Ubicación:** `D:\py\@produxion\@SAGE50\Sage50BI` (repo principal/aplicación de escritorio).
- **Repos satélite (catálogo de plantillas):**
  - `repositorio_Sage50bi` — repo **público** de distribución (plantillas cifradas + docs + manifest).
  - `repositorio_Sage50bi_fuente` — repo **privado** de autoría (donde se crean/validan/cifran las plantillas antes de publicarlas).

## 2. Stack tecnológico

- **Python 3.13**, gestor de paquetes `uv`
- **Streamlit** — interfaz web del catálogo/cuadros de mando (puerto por defecto `55002`)
- **PyODBC / SQL Server** — conexión a la base de datos de Sage 50
- **Pandas, Plotly, Altair** — procesamiento y visualización de datos
- **Google Sheets API (gspread, gspread-dataframe)** — integración bidireccional
- **Outlook/SMTP** — envío de emails
- **FTP** — subida de ficheros
- **ReportLab** — generación de PDFs
- **Cryptography (Fernet)** — cifrado de plantillas SQL
- **PyInstaller** — empaquetado como ejecutable Windows
- **pystray** — icono de bandeja del sistema
- Librerías propias: `libwertyconfig` (licencias, `.pyd` Cython/Nuitka, Windows-only), `libwertylog`, `libwertyupdate`, `pysage50e` (API de conexión a Sage 50)

## 3. Arquitectura de la aplicación principal (Sage50BI)

### Bootstrap y arranque
```
sage50bi.py (bootstrap mínimo)
  └── libwertyupdate.update("sage50bi")   → splash screen + comprobación de actualizaciones
  └── biinicio.main()                     → lógica de toda la aplicación
        ├── load_dotenv()                 → carga .env / config.ini
        ├── Sage50Connection.connect()    → pysage50e.apiSAGE50() + validación de licencia
        │     └── libwertyconfig.x11()    → valida licencia contra servidor licwerty
        ├── _mostrar_error_sage50()       → notifica errores de conexión/licencia al usuario
        └── (si éxito) → modo tray / servicio / CLI / Streamlit
```

`biinicio.py` es el módulo central: contiene **todos los modos de ejecución** (tray, CLI, servicio, configuración, monitor, cifrado, empaquetado).

### Módulos `core/` (núcleo de la app)
| Módulo | Responsabilidad |
|---|---|
| `ejecutor.py` | `Sage50Connection` — conexión a Sage 50 y validación de licencia |
| `settings.py` | Configuración centralizada (`.env`), variables `ENTORNO`, `SERVICIO`, `ARRANQUE_CUADROS` |
| `log.py` | Logging centralizado vía `libwertylog` |
| `sage50_license.py` | Helpers de licencia (formato licwerty) |
| `database.py` | Acceso a base de datos |
| `biproceso_v2.py` | Procesamiento de consultas/cuadros de mando |
| `catalogo.py` | Integración del catálogo de plantillas dentro de la app |
| `crud.py` | Operaciones CRUD de entidades internas |
| `entorno.py` | Gestión de entornos multi-empresa |
| `scheduler.py` / `cron.py` | Programación de tareas automáticas (envíos recurrentes) |
| `usuarios.py` | Gestión de usuarios |
| `premium.py` | Lógica de planes/funcionalidades premium |
| `onboarding.py` | Flujo de bienvenida/alta de nuevos usuarios |
| `email_templates.py` | Plantillas de correo |
| `streamlit_launcher.py` | Lanzamiento del servidor Streamlit interno |
| `migracion_v1.py` | Migración desde versión anterior |
| `console.py` | Salida de consola/CLI |
| `app_shutdown.py` | Cierre limpio de la aplicación |

### Scripts de nivel raíz (funcionalidad histórica/v1)
| Archivo | Función |
|---|---|
| `biinicio.py` | Entry point y lógica principal (todos los modos) |
| `bistream.py` | Interfaz Streamlit (editor SQL, dashboards) |
| `biproceso.py` (referenciado) | Motor de procesamiento de cuadros de mando y filtrado |
| `bicreasql.py` | Generación/asistencia de SQL |
| `biplantillasql.py` | Biblioteca de plantillas SQL predefinidas |
| `biemail.py` | Envío automatizado de informes por email (Outlook/SMTP) |
| `bienviovarios.py` | Envíos múltiples/masivos |
| `biftp.py` | Subida de ficheros a FTP |
| `bigoogle.py` | Sincronización con Google Sheets |
| `bixls.py` | Exportación a Excel |
| `bicsv.py` | Exportación a CSV |
| `biword.py` | Exportación/generación de documentos Word |
| `bi_impresion_pdf.py` | Generación de informes en PDF |
| `cuadro.py` | Lógica de cuadros de mando |

## 4. Funcionalidades principales (core / MVP)

1. **Asistente IA para SQL** — genera consultas SQL a partir de lenguaje natural (ej. "Ventas por cliente del último trimestre").
2. **Editor SQL avanzado** — resaltado de sintaxis, validación en tiempo real, formateo (en Streamlit).
3. **Biblioteca de plantillas SQL** — catálogo de consultas predefinidas (ventas, stock, pedidos pendientes...).
4. **Cuadro de mando interactivo** — tablas dinámicas (pivot tables) con arrastrar/soltar.
5. **Filtrado temporal inteligente** — por año, trimestre, mes, día.
6. **Exportación** — a Excel, CSV, PDF, Word.
7. **Automatización de envíos por email** — Outlook o SMTP, programables.
8. **Gestión dinámica de destinatarios** — mediante SQL (ej. enviar comisiones a cada vendedor).
9. **Conectividad FTP** — subida automática de precios/stock/informes.

## 5. Funcionalidades avanzadas (v2 / en progreso)

- Integración con **Google Sheets** (bidireccional, gspread).
- **Dashboard web multiusuario** vía Streamlit con roles de acceso.
- **Portal de autoservicio de plantillas** (catálogo web, venta y distribución — ver sección 7).
- **Generación de PDF** con branding corporativo.
- **Sistema de licencias** — modo demo y activación por empresa (licwerty, `libwertyconfig`).
- **Cifrado de plantillas SQL** (Fernet) para proteger propiedad intelectual.
- **Modo servicio** — ejecución en segundo plano (`SERVICIO=True`) sin interfaz.
- **Estadísticas descriptivas automáticas** (pandas `describe()`).
- **Icono de bandeja del sistema** (pystray).

## 6. Integraciones con Sage 50 y externas

- **Sage 50 / SQL Server** — vía `pysage50e.apiSAGE50()` y ODBC; lee `config.ini` para credenciales.
- **Licencias** — validación contra servidor propio "licwerty" (`libwertyconfig.x11()`), soporta modo demo.
- **Google Sheets** (gspread) — implementado.
- **Multiempresa** — cada empresa en subcarpeta `Sage50Bi/<empresa>/`, variable `EMPRESA`.
- **Integraciones propuestas/futuras** (no confirmadas como implementadas): Teamleader CRM, Shopify, Microsoft Power BI, WhatsApp Business API, almacenamiento en la nube (Dropbox/OneDrive/Google Drive).

## 7. Ecosistema de plantillas: repos `repositorio_Sage50bi*`

Sage50BI se apoya en un **catálogo de plantillas SQL + dashboards Streamlit** gestionado en dos repositorios hermanos:

### `repositorio_Sage50bi_fuente` (privado — autoría)
Aquí se **crean, validan, cifran y publican** las plantillas.

- **Estructura:**
  - `gestion/` — GUI/CLI de gestión (PySimpleGUI/FreeSimpleGUI): `gestor.py` (CRUD), `cifrado.py` (Fernet), `sql_validator.py` (bloquea DDL/DML, solo `SELECT`), `version_manager.py` (SemVer), `readme_generator.py`, `mkdocs_generator.py`, `manifest_generator.py`, `release_manager.py`.
  - `catalogo/` — UI Streamlit embebida en Sage50BI (`catalogo.py`, `detalle.py`, `instalador.py`, `manifest_reader.py`, `recomendaciones.py`).
  - `integracion/` — motor de actualizaciones dentro de Sage50BI (`actualizador.py`, `descargador.py`, `registro.py`).
  - `privado_mantenimiento/` — SQL en claro, **nunca se publica** (gitignored).
- **Flujo:** Autoría (SQL en claro) → Validación (solo SELECT) → Cifrado Fernet → Publicación al repo público → Generación de README/docs MkDocs (ES/CA)/manifest/RSS → `git push` → GitHub Actions → GitHub Pages/Releases.
- **Cifrado:** públicas con `FERNET_KEY_COMPILED` (de `libwertyconfig`); privadas con clave SHA-256 derivada de la licencia del cliente.
- Comandos CLI: `python main.py` (GUI), `stats`, `listar`, `regenerar`, `verificar`, `release` (con `--dry-run`, `--bump`, `--prerelease`, `--version`).

### `repositorio_Sage50bi` (público — distribución)
- Contiene `publicas/`, `privadas/`, `packs/` (bundles JSON), `docs/` (MkDocs bilingüe), `manifest-templates.json` (la "API" que Sage50BI consume), `README.md` autogenerado.
- **Consumo:** Sage50BI lee el manifest → descarga cifrado → descifra → instala.
- Publica releases en GitHub (`releases/latest`) con `manifest-tienda.json` + `plantillas.csv`.

### Sistema de categorías (por rango de ID)
| Rango | Categoría |
|---|---|
| 1–999 | Privadas (por cliente) |
| 1000–1999 | Informes y Listados |
| 2000–2999 | Facturas y Documentos |
| 3000–3999 | Balances y Contabilidad |
| 4000–4999 | Dashboard y Gráficos |

### Reglas de seguridad clave
- Solo se permiten sentencias `SELECT` (bloqueadas: `CREATE VIEW`, `ALTER`, `DROP`, `INSERT`, `UPDATE`, `DELETE`).
- `privado_mantenimiento/` nunca se sube al control de versiones.
- README público es autogenerado, no editable a mano.
- SemVer obligatorio; documentación bilingüe (ES/CA).

## 8. Modelo de negocio / operación comercial (en definición)

El documento `AUTOSERVICIO_PAQUETES_Y_OPERACION_COMERCIAL.md` describe un sistema de **paquetes autoservicio** para que el cliente descubra, compre e instale plantillas/cuadros de mando:

- Cada plantilla/cuadro se distribuye como `.zip` con estructura fija: `manifest.json`, `README_INSTALACION.md`, `assets/` (SQL, script del cuadro, metadata).
- `manifest.json` define: id, nombre, versión, tipo (`template-pack`), plan requerido (ej. `premium`), si requiere suscripción/clave zip, compatibilidad con versión de Sage50BI.
- Objetivo: que el cliente pueda descubrir → saber si está incluido en su plan → descargar el paquete correcto → instalar sin fricción → saber qué soporte tiene disponible.

## 9. Notas de arquitectura / estado técnico (hallazgos de auditoría interna, `context.md`)

- El logging (`core/log.py`) usa `libwertylog.logger` como singleton; existe un bug conocido: la variable `DEBUG` no controla el nivel de log (solo afecta a `print()`/redirección de stdout), pese a existir un helper `is_debug()` sin usar.
- `DEBUG` se lee de forma dispersa en ~10 archivos vía `os.getenv()`, sin centralizar en `settings.py`.
- Riesgo de seguridad detectado: la clave de licencia cifrada del cliente se filtra en texto plano (ofuscado) en mensajes de error (`core/ejecutor.py`), cuando la validación de licencia falla.
- El estado `network_error` del servidor de licencias no se distingue de licencia inválida, generando mensajes confusos al usuario.

## 10. Casos de uso documentados (IDEAS.md)

- Informes semanales automáticos por vendedor (ahorro de horas de trabajo manual).
- Control de stock con dashboard interactivo (stock actual vs. mínimo, sugerencias de pedido).
- Reconciliación mensual de facturas para asesorías con múltiples empresas cliente.

## 11. Preguntas frecuentes recogidas (para documentación de usuario)

- **Instalación:** `uv sync`, Python 3.13+, empaquetado con `pyinstaller sage50bi.spec`, configuración de conexión en `config.ini`.
- **Fallo de conexión:** valida licencia y conexión vía `libsage50`/`pysage50e`; error visible al usuario, opción de autenticación SQL o Windows integrada.
- **Multiempresa:** carpeta `Sage50Bi/<empresa>/`, variable `EMPRESA`.
- **Formatos soportados:** entrada SQL directo a Sage 50; salida Excel, CSV, PDF, Google Sheets, HTML (dashboard web).
- **Programación de informes recurrentes:** vía `biemail.py`/`biftp.py` y modo servicio (`SERVICIO=True`).

---

Este resumen cubre: propósito, stack, arquitectura de bootstrap y núcleo (`core/`), scripts funcionales de primer nivel, funcionalidades MVP y v2, integraciones con Sage 50 y externas, el ecosistema completo de plantillas (dos repos hermanos, flujo de autoría-publicación-consumo, cifrado, categorías, reglas de seguridad), el modelo de paquetes/autoservicio comercial en definición, y hallazgos técnicos de auditoría interna relevantes para documentación de mantenimiento.
