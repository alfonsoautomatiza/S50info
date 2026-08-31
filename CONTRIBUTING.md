# Contributing — S50Info

Gracias por interesarte en mejorar S50Info. Este proyecto usa un flujo **issue-first**
y **RDD (Receipt-Driven Development)** para que cada cambio tenga una invariante
causal explícita y una validación independiente antes de mergear a `main`.

## TL;DR

1. Buscá o abrí una [issue](../../issues) (usá los templates: bug, feature, chore).
2. Esperá la label `status:approved` (te la pone el maintainer tras revisar evidencia).
3. Creá una rama desde `main` siguiendo el naming `type/descripcion-corta-kebab`.
4. Hacés los cambios con [Conventional Commits](#conventional-commits).
5. Abrís PR con `Closes #N` en el body y exactamente una label `type:*`.
6. Pasás los gates automáticos y el review.
7. Merge a `main`.

## Pre-requisitos

- **Python 3.13+** (gestionado con [uv](https://github.com/astral-sh/uv)).
- **Windows** para build completo (`uv run python c/build_exe.py` y MSIX).
- **Linux/WSL** solo para tests y desarrollo de scripts Python que no tocan pyodbc.
  En WSL **siempre** usar `.venvlinux` para no pisar el `.venv` de Windows:

  ```bash
  UV_PROJECT_ENVIRONMENT=.venvlinux uv sync
  UV_PROJECT_ENVIRONMENT=.venvlinux uv run pytest
  ```

- **ODBC Driver 17 for SQL Server** instalado en Windows si vas a probar contra SAGE50.
- **gh CLI** autenticado (`gh auth status`) para abrir issues y PRs.

## Flujo de trabajo

### 1. Issue primero

No abras una PR sin issue aprobada. Si encontrás un bug o querés una feature:

- Buscá primero si ya existe una issue (cerrada o abierta).
- Si no existe, abrí una usando el template correspondiente (`.github/ISSUE_TEMPLATE/`).
- Completá **todos** los campos requeridos. Sin evidencia de reproducción, una bug no
  puede pasar a `status:approved`.

**Pre-submission privacy review**: antes de mandar la issue, sanitizá nombres de
proyecto, usernames, hosts, paths absolutos y credenciales. Usá placeholders
`<project-name>`, `<user>`, `<host>:<port>`, `<token>`, etc.

### 2. Aprobación

El maintainer revisa la issue y, si está bien fundamentada y reproducible,
le pone la label `status:approved`. Sin esa label, la PR no puede mergear
(gate automático en `.github/workflows/pr-validation.yml`).

### 3. Branch

Branch naming (regex obligatoria):

```
^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$
```

Ejemplos:

- `feat/export-csv-utf8-bom`
- `fix/reset-log-truncates-error`
- `chore/upgrade-typer-15`
- `docs/rdd-workflow`

Creá siempre la rama desde `main` actualizado:

```bash
git fetch origin
git checkout -b feat/mi-cambio origin/main
```

### 4. Conventional Commits

Cada commit debe matchear:

```
^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9._-]+\))?!?: .+
```

Ejemplos:

```
feat(export): agregar formato ndjson
fix(sql): rechazar SELECT INTO en guard de solo-lectura
docs(manual): documentar flag --sqlyear
chore(deps): bump polars a 1.37
refactor(proceso): extraer validación de licencia
```

**Breaking change**: agregar `!` antes de los dos puntos:

```
feat(cli)!: cambiar default de --formato de txt a csv
```

### 5. PR

- Body debe incluir `Closes #N` (o `Fixes #N` / `Resolves #N`).
- Agregá **exactamente una** label `type:*` (ver tabla abajo).
- Completá el template `.github/PULL_REQUEST_TEMPLATE.md` (test plan, budget, checklist).
- Budget: < 400 adiciones + deletions. Si excede, abrí chain PRs o pedí excepción.

| Label de PR         | Tipo de cambio                              |
|---------------------|---------------------------------------------|
| `type:bug`          | Bug fix                                     |
| `type:feature`      | Nueva feature                               |
| `type:docs`         | Solo documentación                          |
| `type:refactor`     | Refactor sin cambio funcional               |
| `type:chore`        | Mantenimiento, tooling, build, deps         |
| `type:breaking-change` | Cambio breaking (CLI, schema, build)     |

### 6. Gates automáticos (no se pueden skipear)

El workflow `pr-validation.yml` corre 5 jobs en cada PR:

1. `Check Issue Reference` — body contiene `Closes/Fixes/Resolves #N` (con guard de contexto negativo).
2. `Check Issue Has status:approved` — **toda** issue linkeada (no solo la primera) tiene esa label.
3. `Check PR Has Exactly One type:* Label` — PR tiene exactamente una.
4. `Check Conventional Commits` — los commits del branch matchean la regex
   (se excluyen los merge commits auto-generados por GitHub).
5. `Tests (pytest)` — corre `uv run pytest` en Linux. Marcado `continue-on-error: true`
   mientras el set de tests esté inmaduro; promover a bloqueante cuando el set
   tenga cobertura real y un umbral de pase explícito.

### 7. Review y merge

- Squash merge a `main` con commit message conventional.
- Borrá la rama después del merge.

## Tests

```bash
UV_PROJECT_ENVIRONMENT=.venvlinux uv sync
UV_PROJECT_ENVIRONMENT=.venvlinux uv run pytest -q
```

Si agregás tests, mantenelos junto al código que cubren (mismo directorio).

## Estilo de código

- **Python**: ruff (config en `pyproject.toml` cuando se agregue).
- **Type hints**: obligatorios en funciones nuevas.
- **Docstrings**: una línea para funciones simples, multi-línea para públicas.
- **Logs**: usar el módulo `logging`, no `print`, salvo CLI output rico (Rich).

## Sanitización

Antes de cada commit, verificá que no commiteás:

- `config.ini` con credenciales reales (debe estar en `.gitignore`).
- Paths absolutos con tu username (`C:\Users\<tu-user>\...`, `/home/<tu-user>/...`).
- Logs con datos de clientes.
- Certificados, licencias, o `*.lic`.

## Release / MSIX

Los releases a Microsoft Store se manejan exclusivamente desde Partner Center
vía MSIX (ver `c/build_exe.py` y `msix/`). El repo no genera ZIPs de
distribución ni auto-updater desde GitHub Releases.

## Más info

- Flujo RDD detallado: [`docs/rdd-workflow.md`](docs/rdd-workflow.md).
- PRD del producto: [`PRD.md`](PRD.md).
- Diseño: [`DESIGN.md`](DESIGN.md).
- Manual técnico: `manual/index.md` (publicado en GitHub Pages).
