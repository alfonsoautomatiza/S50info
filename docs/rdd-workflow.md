# RDD — Receipt-Driven Development en S50Info

> Skill de referencia: [`rdd-defect-workflow`](https://github.com/wertyMSD/s50info).
> Activado solo cuando el switch `gentle-ai review mode` está **on**.

Este documento describe cómo corre RDD en este repositorio. El switch lo
controla el maintainer (`gentle-ai review mode enable|disable|status`).
Cuando está **off**, este documento no aplica y se vuelve a la política
ordinaria (`disabled/unmanaged`).

## 1. Qué es un "recibo"

Un recibo (receipt) es un registro firmado que el motor de review mantiene
sobre un cambio candidato contra un `base_ref`. Contiene:

- **lineage**: identificador de la bounded review transaction.
- **correction**: si se aplicó una corrección bounded, queda registrada.
- **final evidence**: la evidencia del flujo aprobado.
- **base_ref**: el commit exacto contra el que se mide el cambio.

No podés avanzar a `finalize` sin evidencia; no podés publicar sin
`final_verification_passed: true` declarado por el verificador independiente.

## 2. Cuándo aplica RDD acá

Aplica a todo cambio que toque uno de estos paths:

- `s50info.py`, `s50proceso.py`, `s50setup.py`, `s50onboarding.py`,
  `s50exportador_resultados.py`.
- `c/` (build, Cython, MSIX).
- `msix/` (packaging).
- `pyproject.toml`, `pydobj.toml`, `s50info.spec`.

Cambios que **no** requieren RDD formal (siguen issue-first pero no START):

- Docs en `manual/` y `docs/` (excepto este archivo).
- `test/` cuando agrega cobertura sin tocar producción.
- CI / workflows (la PR misma valida).

## 3. El flujo

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Issue        │    │ Branch +     │    │ PR + review  │    │ Merge a      │
│ aprobada     │───►│ cambios      │───►│ con recibo   │───►│ main         │
│ (status:     │    │ (base_ref)   │    │ (START→FINAL │    │              │
│  approved)   │    │              │    │  →VALIDATE)  │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 3.1. Issue aprobada

Toda transacción RDD arranca con una issue `status:approved`. Sin esto,
el gate de PR (`pr-validation.yml`) bloquea el merge.

La issue debe declarar:

- **Invariante causal**: una sola oración, qué propiedad del sistema protege.
- **Operator flows**: lista de flujos CLI / lifecycle afectados.
- **Negative controls**: qué casos NO deben romperse.
- **Rollback**: cómo revertir.

### 3.2. Branch y `base_ref`

Branch desde `main` actualizado:

```bash
git fetch origin
git checkout -b feat/<descripcion> origin/main
```

`base_ref` por convención es `origin/main` (o el SHA del último release tag
si el cambio se basa contra un release concreto).

### 3.3. Cambios con budget

Hard limit: **400 adiciones + deletions por PR**. Por encima:

1. **STOP**. No commitees más.
2. Abrí chain PRs (`chained-pr` skill).
3. O pedí excepción explícita al maintainer con justificación.

### 3.4. PR con recibo

Al abrir la PR:

1. `gh pr create` con body linkeando la issue (`Closes #N`).
2. Label `type:*` correspondiente.
3. El maintainer (o un actor de review) corre:

   ```bash
   gentle_review start --mode ordinary --base-ref origin/main
   ```

   Esto congela el scope, el risk tier y el budget. Devuelve un `lineage_id`.

4. El implementador trabaja y al terminar corre:

   ```bash
   gentle_review finalize --lineage <lineage_id> \
       --correction-line-forecast <n> \
       --validation <doc> \
       --final-evidence <evidencia>
   ```

5. Un verificador independiente corre:

   ```bash
   gentle_review validate --lineage <lineage_id> --command merge
   ```

   Si pasa, devuelve `final_verification_passed: true` y la PR se puede mergear.

### 3.5. Una corrección por transacción

Si la START requiere ajuste, hay **una sola** oportunidad de corrección dentro
de la misma transacción (`finalize` admite un correction_line_forecast). Si la
corrección excede el budget o el scope, se cierra la transacción y se abre
una nueva con una issue derivada.

## 4. Evidencia de flujos

Cada flujo CLI tocado por el cambio necesita evidencia en el PR (test plan):

| Comando probado                                  | Output esperado                          |
|--------------------------------------------------|------------------------------------------|
| `uv run s50info info`                            | Panel con conexión y versión             |
| `uv run s50info sql "select 1"`                  | Tabla Rich con header `1`               |
| `uv run s50info export "select 1" --formato csv` | Archivo CSV en `resultados/`            |
| `uv run s50info reset`                           | Confirmación de truncate (con `--yes`)  |

Si el flujo requiere SAGE50 instalado y el dev no tiene acceso, marcar como
**journey E2E diferido** y justificar; el maintainer corre el journey antes de
mergear.

## 5. Cuando NO usar RDD formal

- Cambios puramente cosméticos (typo, formato) → `type:chore`, una PR normal,
  sin START.
- Refactors sin cambio funcional observables → `type:refactor`, una PR normal,
  con test plan robusto pero sin START salvo que el refactor toque invariantes
  críticas (ej: el guard de solo-lectura, el path de MSIX, la resolución de
  licencia).
- Hotfix de seguridad crítico → bypass de RDD, pero con PR + issue de
  seguimiento dentro de 24h para revisión formal.

## 6. Bypass y recovery

Si una transacción RDD queda en estado inválido (cambio de autoridad, base_ref
que se movió, etc.):

- **NO** llames a `RESET`/`RECOVER` sin pedir consentimiento explícito al
  maintainer. Estas operaciones son destructivas.
- En cambio, abrí una issue describiendo el problema y referenciando el
  `lineage_id` afectado.

## 7. Referencias

- Skill: `rdd-defect-workflow`.
- Branch PR skill: `branch-pr`.
- Issue creation skill: `gentle-ai-issue-creation`.
- Switch: `gentle-ai review mode status` (read-only).
