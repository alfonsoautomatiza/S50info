# Plan 001: Mandatory Microsoft Store update gate for MSIX installs

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat c13bd8a..HEAD -- s50info.py test/test_cli.py msix/AppxManifest.xml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (new Windows/WinRT integration; mitigated by fail-open policy)
- **Depends on**: none
- **Category**: direction (new capability)
- **Planned at**: commit `c13bd8a`, 2026-08-21

## Why this matters

s50info ships to the Microsoft Store as an MSIX package (`InfoMSD.s50info`).
Store auto-updates are optional and often lag days behind a release, so
clients keep running old versions indefinitely. The product owner wants a
**mandatory update gate**: on every launch of a Store-installed s50info, the
app must ask the Store whether an update exists; if one does, it opens the
Store's updates window and refuses to continue until the user updates and
relaunches. This keeps every client on the certified current version.

## Current state

- `s50info.py` — CLI entry (Typer app). The `main()` callback handles quick
  flags first, then initializes state and dispatches subcommands
  (`s50info.py:297-331`):

  ```python
  @app.callback(invoke_without_command=True)
  def main(
      ctx: typer.Context,
      grupo_comunes: str | None = typer.Option(...),
      manual: bool = typer.Option(False, "--manual", "-m", "--m", ...),
      version: bool = typer.Option(False, "--version", "-v", "--v", ...),
  ):
      if version:
          rprint(f"s50info v{S50INFO_VERSION}")
          _recordar_ayuda()
          raise typer.Exit()
      if manual:
          _abrir_manual()
          rprint(f"[grey70]Manual: {MANUAL_URL}[/grey70]")
          _recordar_ayuda()
          raise typer.Exit()

      _inicializar_directorio_trabajo()
      s50onboarding.mostrar_if_necesario(_app_state_dir())
      ...
  ```

  There is **no in-app update check anywhere today**: the pyupdategit
  manifest machinery (`c/build_exe.py`, `c/RELEASE/release.py`) is
  build/release-side only.

- `msix/AppxManifest.xml` — Store package identity:
  `Name="InfoMSD.s50info"`, `Publisher="CN=D75F3D07-BF68-4BB3-B36C-5A12A1A03277"`,
  `MinVersion="10.0.17763.0"` (Windows 10 1809 — matters: the Store API used
  below requires 1809+).
- `s50setup.py:255-267` — `_abrir_url(url)`: repo's canonical way to open a
  URL robustly in frozen builds (`os.startfile` on win32 with
  `webbrowser.open` fallback). The new module must reuse this pattern.
- `test/test_cli.py:28-74` — `load_s50info_module()`: injects fake modules
  (`pysage50e`, `s50proceso`, `s50onboarding`) into `sys.modules` around the
  import, restores them in `finally`, then mocks module attributes. The new
  `s50store` module must be injected the same way or the CLI tests will hit
  the real Windows code paths.
- Conventions: user-facing console copy is Spanish; rich markup with
  `[grey70]` for secondary lines (NOT `[dim]` — invisible on dark themes);
  Windows-only APIs are always guarded by `sys.platform == "win32"` +
  `getattr(os, "startfile", None)` and lazy imports (see `s50setup.py:255`).
- Test runbook (WSL): `.venvlinux/bin/python -m pytest ...` directly, never
  `uv run` (AGENTS.md).

## Design decisions (binding for the executor)

1. **New module `s50store.py`** at repo root, next to `s50setup.py`. No new
   pip dependencies. All Windows API access is lazy (inside functions) so
   the module imports cleanly on the WSL test host.
2. **Packaged-detection**: `ctypes.windll.kernel32.GetCurrentPackageFamilyName`
   two-call dance. Returns the package family name (e.g.
   `InfoMSD.s50info_kdj3h...`) when running with Store package identity,
   `None` otherwise (non-zero return code / non-Windows). ZIP installs have
   no package identity → gate silently skips them.
3. **Store update check**: Windows PowerShell 5.1 subprocess (`powershell.exe`,
   NEVER `pwsh` — PowerShell 7 dropped WinRT) calling the WinRT
   `Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager
   .GetIsAppUpdateAvailableAsync(packageFamilyName)` (available since 1809;
   the MSIX MinVersion is 17763 so this is guaranteed). The exact script is
   given in Step 1. Python parses stdout: `"True"` → `True`,
   `"False"` → `False`, anything else (`Timeout`/`Error`/empty/non-zero
   exit) → `None`.
4. **Fail-open policy (critical)**: the ONLY outcome that blocks the user is
   a definitive `True` from the Store check. `None` (timeout, Store service
   down, offline, PowerShell quirks) and `False` always continue normally.
   Rationale: a mandatory gate that dead-locks a paying customer because the
   Store service hiccupped is worse than a missed update. Log at debug/info
   level when the check could not run.
5. **Blocking behavior**: when an update exists, print a Spanish message,
   open `ms-windows-store://downloadsandupdates` (the Store's "Downloads &
   updates" window — this is "la ventana" the owner asked for), then
   `raise typer.Exit(1)`. The user updates in the Store window and
   relaunches. Do NOT loop-and-wait inside the process: the Store may
   terminate/replace the package during the update, and a blocked console
   breaks Task Scheduler runs (exit code 1 correctly fails them loudly).
6. **Gate placement**: inside `main()`, AFTER the `version`/`manual` quick
   flags (informational commands stay available even when gated) and BEFORE
   `_inicializar_directorio_trabajo()` — so every subcommand (`info`, `sql`,
   `export`, `run`, `reset`, default flow) and the onboarding are gated.
7. **Auto-triggering the update programmatically**
   (`UpdateAppByPackageFamilyNameAsync`) was considered and rejected: the
   owner explicitly asked to open the Store window so the client performs
   the update.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Compile check | `.venvlinux/bin/python -m py_compile s50store.py s50info.py` | exit 0 |
| New module tests | `.venvlinux/bin/python -m pytest test/test_store.py -q` | all pass |
| CLI tests | `.venvlinux/bin/python -m pytest test/test_cli.py -q` | all pass |
| Full suite | `.venvlinux/bin/python -m pytest test/ -q` | all pass (170 + new) |

(From WSL in the repo root, per AGENTS.md. Do NOT run `uv run`.)

## Scope

**In scope** (the only files you should modify/create):
- `s50store.py` (create)
- `s50info.py` (one import + one gate call inside `main()`)
- `test/test_store.py` (create)
- `test/test_cli.py` (extend `load_s50info_module` + 2 new tests)
- `plans/README.md` (status row)

**Out of scope** (do NOT touch):
- `msix/*`, `c/*` — build/packaging pipeline. PyInstaller collects
  `s50store.py` automatically as a static import of `s50info.py`; the
  PowerShell child process needs no bundling.
- ZIP-distribution update gating (pyupdategit manifest check) — different
  distribution channel with its own updater; explicitly deferred.
- `s50proceso.py`, `s50setup.py`, `s50onboarding.py` — not involved in the gate.

## Git workflow

- Work on the current branch (repo works directly on `master` with uncommitted
  changes present — leave existing dirty files untouched; stage only your
  in-scope files if asked to commit).
- If asked to commit: conventional commits, no AI attribution, Spanish-free
  message style like `feat: puerta de actualización obligatoria de la Store`.
  Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Create `s50store.py`

Create `s50store.py` at the repo root with exactly this structure:

```python
"""Puerta de actualización obligatoria desde Microsoft Store (instalaciones MSIX).

Solo actúa cuando s50info corre con identidad de paquete Store (MSIX).
Política fail-open: únicamente un `True` definitivo de la Store bloquea;
timeout/error/sin-paquete nunca bloquean al cliente.
"""

import logging
import subprocess
import sys

_logger = logging.getLogger(__name__)

STORE_UPDATES_URI = "ms-windows-store://downloadsandupdates"

_PS_CHECK = """
param([string]$FamilyName)
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $null = [Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager,Windows.ApplicationModel.Store.Preview.InstallControl,ContentType=WindowsRuntime]
  $mgr = New-Object Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager
  $op = $mgr.GetIsAppUpdateAvailableAsync($FamilyName)
  $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  } | Select-Object -First 1
  $task = $asTask.MakeGenericMethod([bool]).Invoke($null, @($op))
  if ($task.Wait(15000)) { Write-Output $task.Result } else { Write-Output 'Timeout' }
} catch {
  Write-Output 'Error'
}
"""


def package_family_name() -> str | None:
    """Family name del paquete Store, o None si no hay identidad de paquete."""
    if sys.platform != "win32":
        return None
    import ctypes

    kernel32 = ctypes.windll.kernel32
    size = ctypes.c_uint32(0)
    rc = kernel32.GetCurrentPackageFamilyName(ctypes.byref(size), None)
    if rc != 0 and rc != 122:  # 122 = ERROR_INSUFFICIENT_BUFFER (primer paso)
        return None
    buffer = ctypes.create_unicode_buffer(size.value)
    rc = kernel32.GetCurrentPackageFamilyName(ctypes.byref(size), buffer)
    return buffer.value if rc == 0 and buffer.value else None


def _consultar_tienda(family_name: str) -> bool | None:
    """True/False según la Store; None si no se pudo consultar (fail-open)."""
    try:
        resultado = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", _PS_CHECK, "-", family_name],
            capture_output=True, text=True, timeout=25, creationflags=0x08000000,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _logger.info("store: consulta no disponible: %s", exc)
        return None
    salida = (resultado.stdout or "").strip()
    if resultado.returncode == 0 and salida == "True":
        return True
    if resultado.returncode == 0 and salida == "False":
        return False
    _logger.info("store: respuesta no concluyente (rc=%s, out=%r)",
                 resultado.returncode, salida[:80])
    return None


def abrir_tienda_actualizaciones() -> None:
    """Abre la ventana Descargas y actualizaciones de Microsoft Store."""
    import s50setup

    s50setup._abrir_url(STORE_UPDATES_URI)


def verificar_y_bloquear_si_necesario() -> bool:
    """Puerta de actualización obligatoria. True = hay que bloquear y salir.

    Fail-open: cualquier fallo de consulta deja continuar.
    """
    family = package_family_name()
    if not family:
        return False
    if _consultar_tienda(family) is not True:
        return False

    from rich import print as rprint

    rprint(
        "[bold yellow]Hay una actualización obligatoria de s50info disponible "
        "en Microsoft Store.[/bold yellow]"
    )
    rprint(
        "Se abrió la ventana de actualizaciones de la Store: actualiza "
        "s50info y vuelve a ejecutar el programa."
    )
    rprint("[grey70]No puedes continuar con esta versión.[/grey70]")
    abrir_tienda_actualizaciones()
    return True
```

Notes:
- `creationflags=0x08000000` (CREATE_NO_WINDOW) prevents a console flash in
  the frozen windowed build; harmless otherwise. Verify this constant is
  acceptable; if the frozen build is console-only, it may be dropped.
- `-Command <script> - <arg>` passes `$FamilyName` positionally after the
  script dash. If testing shows the argument is not bound, switch to
  `-Command` with the family name embedded via a formatted placeholder —
  but ONLY after quoting it, since it comes from the OS, not the user.

**Verify**: `.venvlinux/bin/python -m py_compile s50store.py` → exit 0.
Also: `.venvlinux/bin/python -c "import s50store; print(s50store.package_family_name())"`
→ prints `None` (WSL is not win32).

### Step 2: Create `test/test_store.py`

Model after `test/test_onboarding.py` (plain pytest functions, module import
via `sys.path` insertion at top — copy lines 1-12 of that file for the
header). Cover:

1. `package_family_name()` returns `None` on non-win32 (mock
   `sys.platform` via `monkeypatch.setattr(sys, "platform", "linux")` if the
   host is Windows, else it is trivially None on WSL — write the test so it
   passes on BOTH hosts by monkeypatching).
2. `_consultar_tienda` parsing matrix — monkeypatch
   `subprocess.run` to return objects with `(returncode=0, stdout="True")`,
   `(0, "False")`, `(1, "True")`, `(0, "Timeout")`, `(0, "")`, and to raise
   `subprocess.TimeoutExpired`; expect `True`, `False`, `None`, `None`,
   `None`, `None`.
3. `verificar_y_bloquear_si_necesario()`:
   - no package → `False` and no subprocess call (monkeypatch
     `package_family_name` → `None`, patch `_consultar_tienda` with a
     MagicMock and assert not called);
   - package + Store says `True` → returns `True`, calls
     `abrir_tienda_actualizaciones` (monkeypatched) and prints
     "actualización obligatoria" (capture with `capsys`);
   - package + Store says `None` (fail-open) → returns `False`, nothing
     printed.

**Verify**: `.venvlinux/bin/python -m pytest test/test_store.py -q` → all pass.

### Step 3: Wire the gate into `s50info.py` and extend the CLI test loader

3a. In `s50info.py`, next to `import s50setup` / `import s50onboarding`
(top of file, ~line 18-20), add:

```python
import s50store
```

3b. Inside `main()`, immediately AFTER the `if manual:` block and BEFORE
`_inicializar_directorio_trabajo()` (~line 331), add:

```python
    if s50store.verificar_y_bloquear_si_necesario():
        raise typer.Exit(1)
```

3c. In `test/test_cli.py`, extend `load_s50info_module` exactly like the
`s50onboarding` entries: add `"s50store": sys.modules.get("s50store")` to
the `mocked` dict, `sys.modules["s50store"] = MagicMock()` beside line 58,
and after the import (beside line 68) add
`module.s50store.verificar_y_bloquear_si_necesario = MagicMock(return_value=False)`.

3d. Add two tests to `test/test_cli.py` (model after
`test_default_flow_calls_info_command`):

```python
def test_store_update_gate_blocks_before_subcommand():
    module, _, mock_proceso_module, _ = load_s50info_module()
    module.s50store.verificar_y_bloquear_si_necesario = MagicMock(return_value=True)

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 1
    mock_proceso_module.proceso.assert_not_called()
    assert "actualización obligatoria" in result.stdout


def test_store_update_gate_passes_when_no_update():
    module, _, mock_proceso_module, _ = load_s50info_module()
    module.s50store.verificar_y_bloquear_si_necesario = MagicMock(return_value=False)

    result = runner.invoke(module.app, ["info"])

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.info.assert_called_once()
```

**Verify**: `.venvlinux/bin/python -m pytest test/test_cli.py -q` → all pass
(previous 30+ plus 2 new).

### Step 4: Full suite + boundary check

**Verify**:
- `.venvlinux/bin/python -m pytest test/ -q` → all pass, zero failures.
- `git status --short` → only the in-scope files (plus pre-existing dirty
  files already listed in "Current state") are modified.

### Step 5 (Windows host, optional/manual): live smoke check

On the Windows dev machine (NOT from WSL):

1. Standalone PowerShell sanity probe of the WinRT call (any Store package):
   run the `_PS_CHECK` script with `$FamilyName` =
   `(Get-AppxPackage Microsoft.WindowsCalculator).PackageFamilyName`.
   Expect output `True` or `False` — NOT `Error`/`Timeout`. If `Error`,
   that is a STOP condition (the AsTask reflection pattern failed on this OS).
2. Build normally (`c/build_exe.py`), install the MSIX, temporarily publish
   a newer Store version (or use the Store's " slower rollout" test path),
   and confirm: launch → gate message → Store window opens → app exits 1 →
   update → relaunch passes the gate.

## Test plan

Covered by Steps 2-3: parse matrix for the PowerShell contract, fail-open
semantics, gate placement before subcommand dispatch, loader isolation.
Structural pattern: `test/test_cli.py::load_s50info_module` for module
injection; `test/test_onboarding.py` for plain-function test style.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `.venvlinux/bin/python -m py_compile s50store.py s50info.py` exits 0
- [ ] `.venvlinux/bin/python -m pytest test/test_store.py -q` all pass (≥9 tests)
- [ ] `.venvlinux/bin/python -m pytest test/ -q` all pass (170 existing + ≥11 new)
- [ ] `rg -n "verificar_y_bloquear_si_necesario" s50info.py` shows exactly 1 call site inside `main()`
- [ ] `rg -n "s50store" test/test_cli.py` shows loader injection + 2 new tests
- [ ] `git status --short` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The `main()` area in `s50info.py` no longer matches the "Current state"
  excerpt (drift since `c13bd8a`).
- The Windows PowerShell probe (Step 5.1) prints `Error` on a real Windows
  host — the WinRT `AsTask` reflection pattern is not working there; do not
  ship a gate that can never fire (or worse, always fail-closed).
- `GetIsAppUpdateAvailableAsync` is not callable with a single string
  argument on the installed Windows SDK (signature drift) — report the
  actual signature discovered.
- Wiring the gate requires touching any file outside the in-scope list.
- The full suite cannot reach all-pass within two fix attempts.

## Maintenance notes

- **Store certification**: an always-on gate is acceptable Store policy
  (apps may require updates), but keep the fail-open policy — a fail-closed
  gate that bricks offline users violates Store expectations.
- **Rollout coupling**: after publishing a new Store version, expect a
  window where the manifest/ZIP world says "new version" but the Store has
  not finished certification — this gate intentionally only trusts the
  Store's own answer, never the local manifest, to avoid dead-locking users
  on a Store page with no update available.
- **PowerShell 5.1 dependency** is pinned to `powershell.exe`; if the
  project ever moves to pwsh-only hosts, this breaks silently (fail-open)
  — the `_logger.info` line is the place to look.
- **Deferred**: same mandatory gate for ZIP installs via the signed
  pyupdategit manifest (`manifest_url` in `c/product.json`) — separate plan
  if the owner wants it; different trust chain and dead-lock hazards.
