# Agent Notes

## Project
- Project name: `s50info`
- Description: Cli de consulta a SAGE50
- Python version: 3.13
- Package manager: `uv`

## Mandatory workflow
- Use `agent.md` as the single source of truth for agent instructions, project context, conventions, decisions and preferences.
- If instructions need to be added, corrected or updated, update `agent.md`.
- Do not add project rules to `CLAUDE.md`; it must remain only a compatibility bridge to this file.
- Keep work simple and practical.

## Python workflow
- Use `uv` for dependency management.
- Do not use `pip` directly for project dependencies.
- On Windows, use `.venv` as the normal project environment.
- If checks/tests are run from Linux/WSL, use/create `.venvlinux`; do not recreate or modify the Windows `.venv` from Linux/WSL.
- For any Linux/WSL agent command, enforce `UV_PROJECT_ENVIRONMENT=.venvlinux` before `uv run`/`uv sync` to guarantee the Windows `.venv` is never touched.

## Build workflow
- Main build script: `c/build_exe.py`.
- Product metadata lives in `c/product.json`.
- `pydobj.toml` is created separately with `pydobj init`; do not generate it from this template.
- In ZIP mode, `c/build_exe.py` should place generated ZIPs in `c/RELEASE/` so `c/RELEASE/release.py` can consume them.
- In ZIP mode, `c/build_exe.py` also stages the public release into the manual repo (`public_repo` in `c/product.json`): canonical versioned ZIP + `release.json` + `product.json` into `release-assets/`, and signs `manifest-<channel>.json` (same version as `release.json`) into `<updates_dir>/` via `pyupdategit build-manifest`.
- `release-assets/` receives ONLY the ZIP + `release.json` + `product.json`; the MSIX is Store-only and is never copied there.
- MSIX packages are generated exclusively in `D:\c\msix` (not in `c/RELEASE/`).
- In `pyd` mode, compiled `.pyd` staging belongs in `c/RELEASE/_internal`.
- In `full`/`zip` modes, `.last_build` should be generated at the very end of the successful build flow.

## Release workflow
- Publication is orchestrated by the `release-crm` skill from the manual repo's `release-assets/` (ZIP + `release.json` + `product.json`), after `c/build_exe.py` has signed the manifest.
- `c/RELEASE/release.py` is the legacy alternative (signs + deploys on its own).
- Release metadata: `c/RELEASE/release.json`.
- Release documentation: `c/RELEASE/README.md`.
- `release.json.version` must use strict `X.Y.Z` format.
- `release.json.type`, when present, must be `partial` or `full`.
- `UPDATE_PRIVATE_KEY` may be provided from the environment or from `c/RELEASE/.env` (build signs with it; `release-crm` does not need it).
- `manifest_url` is baked into installed binaries: never change its value or the deployed updates path.

## Skills de referencia
- **release-crm** (`C:\Users\alfonso\.config\opencode\skills\release-crm\SKILL.md`): orquesta el release completo. Ejecutar siempre que se publique una versión. Contiene:
  - Flujo de publicación (GitHub Release + gh-pages + README/LICENSE).
  - Modelos de repo (A = distribución separada, B = mismo repo).
  - Prerrequisitos y guardas obligatorias.
  - Botón flotante "Enviar incidencia" (FAB): patrón reutilizable en `assets/` con CSS + HTML override para MkDocs Material.
- **crm-docs-release** (sub-skill): novedades desde Engram + enriquecimiento SEO + gate de imágenes. Se ejecuta ANTES del deploy.
- **crm-docs** (sub-skill): enriquecimiento de documentación (SEO, compresión, imágenes).
- Antes de cada release, revisar si hay mejoras o campos nuevos en estos skills que apliquen a este proyecto.

## Current status
- New project generated from `D:\@plantilla`.
- Review and complete `c/product.json` release paths before first production release.
