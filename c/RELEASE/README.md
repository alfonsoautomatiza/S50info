# Release workflow (`c/RELEASE`)

Este directorio contiene el flujo de publicación de updates del proyecto usando `pyupdategit`, GitHub Releases y MkDocs.

El objetivo del proceso es dejar publicado un `manifest-stable.json` firmado y, según el tipo de release, publicar también el ZIP en la documentación o en GitHub Releases.

## Archivos

- `release.py`: script principal de publicación.
- `release.json`: datos de la release actual: versión, ZIP, notas y tipo opcional.
- `.env` (opcional): clave privada `UPDATE_PRIVATE_KEY` para firmar manifests.
- `../product.json`: configuración principal del producto/proyecto.

## Configuración del proyecto (`../product.json`)

`release.py` busca la configuración en este orden:

1. Ruta indicada por `UPDATE_PRODUCT_CONFIG`, si existe.
2. `c/product.json`.
3. `c/RELEASE/product.json`.
4. `product.json` del directorio actual.

Claves obligatorias:

- `project_id`
- `nombre` o, como alternativa, `product_display_name` / `product_name`
- `key_id`
- `manifest_url`
- `github_owner`
- `github_repo`
- `docs_repo`
- `updates_dir`
- `files_dir`

Claves opcionales:

- `channel`: por defecto `stable`.
- `target`: por defecto `win-x64`.
- `allowlist`: por defecto `["."]`.

Si faltan claves de publicación, el script las añade vacías al `product.json`, se detiene y pide rellenarlas antes de continuar.

## Datos de release (`release.json`)

Ejemplo:

```json
{
  "version": "0.1.0",
  "zip": "proyecto.zip",
  "notes": "",
  "type": "partial"
}
```

Campos:

- `version`: obligatorio. Formato estricto `X.Y.Z`.
- `zip`: obligatorio. Nombre del ZIP dentro de `c/RELEASE/`.
- `notes`: opcional. Se usa como notas de release y en el manifest.
- `type`: opcional. Solo admite `partial` o `full`.

Si la versión de `release.json` no coincide con `product.json`, el script actualiza automáticamente `product.json` a la versión de la release.

## Tipos de release

### `partial`

Se usa para publicar cambios dentro del mismo major.

Qué hace:

1. Descomprime el ZIP temporalmente.
2. Valida que no haya rutas peligrosas con `..`.
3. Calcula SHA-256 de todos los archivos.
4. Genera `operations.json` con operaciones `replace_file`.
5. Genera `checksums.sha256`.
6. Reempaqueta el ZIP final.
7. Copia el ZIP final a:

   ```text
   <docs_repo>/<files_dir>/<zip>
   ```

8. El manifest queda apuntando a:

   ```text
   files/<zip>
   ```

### `full`

Se usa para una release completa, normalmente al cambiar de major o en la primera release.

Qué hace:

1. Crea una release en GitHub con tag `vX.Y.Z`.
2. Sube el ZIP como asset de esa release.
3. El manifest queda apuntando a la URL de descarga de GitHub.
4. Al final, si todo ha ido bien, elimina releases antiguas y deja solo la última.

Si `release.json` fuerza `"type": "full"` en una versión que no parece cambio de major, el script pide confirmación manual escribiendo exactamente `SI`.

## Autodetección del tipo

Si `release.json` no define `type`, el script consulta la última release de GitHub:

- Si no hay releases previas: usa `full`.
- Si el major nuevo es mayor que el anterior: usa `full`.
- En el resto de casos: usa `partial`.

`type` debe ser estrictamente `partial` o `full`; cualquier otro valor aborta el proceso.

## Requisito del ZIP

El ZIP debe contener el marcador:

```text
temp/<project_id>.<version>
```

Ejemplo:

```text
temp/proyecto.0.1.0
```

Si el marcador no existe, `release.py` lo crea automáticamente dentro del ZIP y continúa.

Si el ZIP está corrupto o no se puede abrir, el proceso falla.

## Firma del manifest

El manifest se firma siempre con `pyupdategit build-manifest`.

La clave privada se obtiene en este orden:

1. Variable de entorno `UPDATE_PRIVATE_KEY`.
2. Archivo local `c/RELEASE/.env` con:

   ```env
   UPDATE_PRIVATE_KEY="TU_CLAVE_PRIVADA_BASE64"
   ```

Si no existe clave, el script se detiene y muestra cómo generarla con:

```bash
pyupdategit generate-keys --key-id <key_id>
```

El manifest generado se escribe en:

```text
<docs_repo>/<updates_dir>/manifest-<channel>.json
```

Por defecto:

```text
manifest-stable.json
```

## Publicación con MkDocs

Después de firmar el manifest, el script publica la documentación con:

```bash
mkdocs gh-deploy --force
```

Lo ejecuta dentro de `docs_repo`.

Antes del deploy:

- Limpia completamente `docs/es` para mantener una sola release publicada.
- Recrea `<docs_repo>/<updates_dir>` antes de escribir el manifest firmado.
- Genera/copía el ZIP y manifest necesarios según el tipo de release.

Después del deploy:

- Elimina la carpeta `site/` generada por MkDocs.

Si `mkdocs` no está instalado o no responde, el manifest puede quedar generado localmente, pero no se publica.

## Pre-checks que realiza el script

Antes de publicar, valida:

- `pyupdategit version` responde.
- `git --version` responde.
- `gh auth status` está autenticado.
- Existe `release.json`.
- `product.json` es JSON válido y contiene la configuración necesaria.
- `release.json` es JSON válido.
- La versión tiene formato estricto `X.Y.Z`.
- El ZIP existe.
- El repositorio `docs_repo` existe antes de ejecutar MkDocs.

## Flujo completo resumido

1. Lee `product.json`.
2. Asegura claves de publicación obligatorias.
3. Ejecuta pre-checks de herramientas (`pyupdategit`, `git`, `gh`).
4. Lee `release.json`.
5. Valida versión y ZIP.
6. Sincroniza la versión en `product.json`.
7. Detecta si la release es `partial` o `full`.
8. Limpia `docs/es`.
9. Comprueba o crea el marcador `temp/<project_id>.<version>` dentro del ZIP.
10. Si es `partial`, genera `operations.json`, `checksums.sha256` y ZIP final en docs.
11. Si es `full`, crea GitHub Release y sube el ZIP.
12. Carga `UPDATE_PRIVATE_KEY` desde entorno o `.env`.
13. Firma el manifest con `pyupdategit build-manifest`.
14. Publica con `mkdocs gh-deploy --force`.
15. Elimina `site/`.
16. Si es `full`, elimina releases antiguas.
17. Muestra URLs finales de manifest y ZIP/release.

## Ejecución

Desde `c/RELEASE/`:

```bash
python release.py
```

También puede ejecutarse desde otro directorio siempre que las rutas de configuración sean correctas, pero lo recomendado es hacerlo desde `c/RELEASE/`.

## Requisitos externos

- `pyupdategit` instalado.
- `git` instalado.
- GitHub CLI (`gh`) instalado y autenticado.
- `mkdocs` disponible para publicar.
- `UPDATE_PRIVATE_KEY` en entorno o en `.env`.
- Acceso al repo de documentación indicado por `docs_repo`.
- Acceso al repo GitHub indicado por `github_owner/github_repo`.

## Errores comunes

### `release.json invalido: version, zip`

Faltan campos obligatorios en `release.json`.

### `Version invalida ... Formato obligatorio: X.Y.Z`

La versión debe ser numérica y con tres partes, por ejemplo `2.1.8`.

### `No encuentro: <zip>`

El ZIP indicado en `release.json` no existe dentro de `c/RELEASE/`.

### `ZIP invalido o corrupto`

El ZIP no se puede abrir. Hay que regenerarlo.

### `UPDATE_PRIVATE_KEY no esta en variables de entorno`

Falta la clave privada para firmar el manifest. Añadirla al entorno o a `c/RELEASE/.env`.

### `mkdocs no esta instalado`

El manifest se ha preparado, pero no puede publicarse hasta instalar MkDocs.

### `docs_repo no existe`

La ruta configurada en `product.json` no existe en este equipo.
