<!-- markdownlint-disable MD041 -->
<!--
  PR template para s50info (RDD-first).

  Reglas duras:
  - Toda PR DEBE linkear una issue con label `status:approved`.
  - Toda PR DEBE tener exactamente UNA label `type:*` (ver sección "Tipo de PR").
  - Conventional Commits (ver CONTRIBUTING.md).
  - Budget de cambios: < 400 adiciones + deletions por PR. Si excede, abrir chain.
  - Tests: `uv run pytest` debe pasar antes de pedir review.
-->

## Linked Issue (REQUERIDO)

> Sin este link la PR no puede mergear. La issue debe tener la label `status:approved`.

Closes #

## Tipo de PR (REQUERIDO — marcar UNA y agregar label matching)

- [ ] Bug fix → agregar label `type:bug`
- [ ] Nueva feature → agregar label `type:feature`
- [ ] Refactor de código → agregar label `type:refactor`
- [ ] Solo documentación → agregar label `type:docs`
- [ ] Mantenimiento / tooling → agregar label `type:chore`
- [ ] Breaking change → agregar label `type:breaking-change`

## Resumen

1-3 bullets de qué hace la PR.

-

## Cambios

| Archivo | Cambio |
|---------|--------|
| `ruta/al/archivo` | Qué se modificó |

## Invariante causal y rollback

- **Invariante que protege esta PR** (una sola, en una línea):
- **Plan de rollback** (cómo revertir si algo sale mal):

## Test Plan

Marca los que apliquen y completá con el output real:

- [ ] `uv run pytest` pasa
- [ ] Probado manualmente el comando afectado (ej: `uv run s50info info`)
- [ ] Si se tocó SQL: `uv run s50info sql "<consulta de prueba>"`
- [ ] Si se tocó export: `uv run s50info export "<consulta>" --formato <fmt>`
- [ ] Si se tocó build: `uv run python c/build_exe.py` (solo Windows)
- [ ] Si se tocó MSIX: validado localmente (no commitear MSIX final)
- [ ] Si se tocó docs: `mkdocs build --strict` pasa
- [ ] `shellcheck` limpio si hay scripts `.sh` o `.ps1`

## Budget de cambios

- Additions: ___
- Deletions: ___
- **Total: ___** (debe ser < 400; si no, justificar abajo)

Si el total excede 400, abrir chain PR (`chained-pr`) o pedir excepción explícita.

## Checklist del contributor

- [ ] Linked una issue con `status:approved`
- [ ] Agregué exactamente UNA label `type:*`
- [ ] Branch naming cumple `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`
- [ ] Conventional Commits en todos los commits del branch
- [ ] Tests pasan localmente
- [ ] Sin secretos, credenciales, ni paths absolutos de usuario
- [ ] Sin trailers `Co-Authored-By`
- [ ] Documentación actualizada si cambió comportamiento
- [ ] Plan de rollback completado en la sección anterior
