#!/usr/bin/env python3
"""
Release rapido de paquete completo (lee product.json + release.json).

Lee product.json (config del proyecto) y release.json (version/zip).
- Publica siempre el ZIP completo en GitHub Releases.
- Genera y despliega el manifest via MkDocs.
- No admite releases parciales: para Microsoft Store/Partner Center se usa paquete completo.

USAGE:
    1) Prepara un zip con los archivos cambiados
    2) Edita release.json con la version y el nombre del zip
    3) Recomendado: corre `pyupdategit publicar` desde la carpeta del proyecto
       para preparar la configuracion del update
    4) Alternativa legacy: ejecuta `python release.py`

NOTES:
    Requiere:
    - UPDATE_PRIVATE_KEY en variables de entorno (para firmar, siempre)
    - pyupdategit instalado (ideal: pipx install pyupdategit)
    - gh CLI logueado (para publicar GitHub Releases)
    - mkdocs instalado (para gh-deploy)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
import zipfile
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath

# ── Colores ───────────────────────────────────────────────────────


def ok(msg: str) -> None:
    print(f"  \033[92m[OK]\033[0m {msg}")


def info(msg: str) -> None:
    print(f"  \033[96m[..]\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"  \033[93m[??]\033[0m {msg}")


def fail(msg: str) -> None:
    print(f"  \033[91m[ERROR]\033[0m {msg}")


# ── Helpers ───────────────────────────────────────────────────────


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a command, return CompletedProcess."""
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, cwd=cwd)


def build_clean_env_for_external_tools() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(key, None)
    return env


def run_mkdocs(
    args: list[str], *, check: bool = True, capture: bool = True, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    env = build_clean_env_for_external_tools()
    if os.name == "nt":
        return subprocess.run(
            ["cmd", "/c", "mkdocs", *args],
            check=check,
            capture_output=capture,
            text=True,
            cwd=cwd,
            env=env,
        )
    return subprocess.run(
        ["mkdocs", *args],
        check=check,
        capture_output=capture,
        text=True,
        cwd=cwd,
        env=env,
    )


def clear_directory_contents(path: Path, label: str) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        ok(f"{label} creado: {path}")
        return

    if not path.is_dir():
        fail(f"{label} no es un directorio: {path}")
        sys.exit(1)

    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    ok(f"{label} limpiado: {path}")


def ensure_safe_updates_cleanup_path(updates_dir: Path, docs_repo_path: Path) -> None:
    """Abort if updates_dir is not a dedicated updates folder."""
    resolved_updates = updates_dir.resolve()
    resolved_docs = docs_repo_path.resolve()

    if resolved_updates.name.lower() != "updates":
        fail(f"updates_dir demasiado amplio o inseguro; debe terminar en 'updates': {resolved_updates}")
        sys.exit(1)
    if resolved_updates == resolved_docs:
        fail(f"updates_dir no puede ser la raiz de docs_repo: {resolved_updates}")
        sys.exit(1)
    if not resolved_updates.is_relative_to(resolved_docs):
        fail(f"updates_dir debe estar dentro de docs_repo: {resolved_updates}")
        sys.exit(1)


def fmt_size(size_bytes: int) -> str:
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000:.1f} KB"


def load_env_value_from_file(env_file: Path, key: str) -> str | None:
    if not env_file.exists():
        return None

    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue

            left, right = raw.split("=", 1)
            if left.strip() != key:
                continue

            value = right.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value
    except OSError:
        return None

    return None


def resolve_product_config(script_dir: Path) -> Path:
    env_override = os.environ.get("UPDATE_PRODUCT_CONFIG", "").strip()
    if env_override:
        candidate = Path(env_override).expanduser()
        if candidate.exists():
            return candidate
        fail(f"UPDATE_PRODUCT_CONFIG apunta a un fichero inexistente: {candidate}")
        sys.exit(1)

    candidates = [
        script_dir.parent / "product.json",
        script_dir / "product.json",
        Path.cwd() / "product.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    fail("No encuentro product.json")
    print("\033[93m  Rutas buscadas:\033[0m")
    for candidate in candidates:
        print(f"    - {candidate}")
    print("\033[93m  Define UPDATE_PRODUCT_CONFIG o crea product.json del proyecto\033[0m")
    sys.exit(1)


def config_text(config: dict, key: str) -> str:
    value = config.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def resolve_config_path(raw_path: str, base_dir: Path) -> Path:
    value = raw_path.strip()
    if os.name != "nt":
        value = value.replace("\\", "/")
        if len(value) >= 3 and value[1:3] == ":/" and value[0].isalpha():
            value = f"/mnt/{value[0].lower()}/{value[3:]}"

    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def get_required_config(config: dict, key: str) -> str:
    value = config_text(config, key)
    if value:
        return value
    env_key = f"UPDATE_{key.upper()}"
    value = os.environ.get(env_key, "").strip()
    if not value:
        raise KeyError(key)
    return value


def config_text_first(config: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = config_text(config, key)
        if value:
            return value
    return default


def child_config_path(config: dict, parent_key: str, child_name: str, *, explicit_key: str = "") -> str:
    """Return an optional explicit path or derive `<parent>/<child>`.

    Ejemplo: si `updates_dir = docs/es/updates`, `files_dir` se deriva como
    `docs/es/updates/files`; no hace falta repetirlo en product.json.
    """
    if explicit_key:
        explicit = config_text(config, explicit_key)
        if explicit:
            return explicit

    parent = get_required_config(config, parent_key).replace("\\", "/").rstrip("/")
    return f"{parent}/{child_name}"


def validate_release_zip_name(raw_name: str) -> str:
    zip_name = raw_name.strip()
    if not zip_name:
        return ""
    if PurePosixPath(zip_name).is_absolute() or PureWindowsPath(zip_name).is_absolute():
        fail("release.json invalido: zip debe ser un nombre de fichero, no una ruta absoluta")
        sys.exit(1)
    parts = zip_name.replace("\\", "/").split("/")
    if len(parts) != 1 or parts[0] in ("", ".", "..") or ".." in parts:
        fail("release.json invalido: zip debe ser un fichero dentro de c/RELEASE, sin carpetas ni '..'")
        sys.exit(1)
    return zip_name


def ensure_zip_readable(zip_path: Path) -> None:
    if not zip_path.exists():
        fail(f"No encuentro: {zip_path}")
        print("\033[93m  Crea el zip y vuelve a intentarlo.\033[0m")
        sys.exit(1)
    if not zip_path.is_file():
        fail(f"ZIP invalido: no es un fichero: {zip_path}")
        sys.exit(1)
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad_member = archive.testzip()
    except (zipfile.BadZipFile, OSError) as exc:
        fail(f"ZIP invalido o corrupto: {zip_path} ({exc})")
        sys.exit(1)
    if bad_member:
        fail(f"ZIP invalido o corrupto: {zip_path} (miembro corrupto: {bad_member})")
        sys.exit(1)


def load_signing_key(script_dir: Path, key_id: str) -> str:
    signing_key = os.environ.get("UPDATE_PRIVATE_KEY")
    if not signing_key:
        env_file = script_dir / ".env"
        signing_key = load_env_value_from_file(env_file, "UPDATE_PRIVATE_KEY")
        if signing_key:
            os.environ["UPDATE_PRIVATE_KEY"] = signing_key
            ok(f"UPDATE_PRIVATE_KEY cargada desde {env_file}")

    if not signing_key:
        fail("UPDATE_PRIVATE_KEY no esta en variables de entorno.")
        print()
        print("\033[93m  Ejecuta esto en tu shell y vuelve a correr release.py:\033[0m")
        print()
        print('    export UPDATE_PRIVATE_KEY="TU_CLAVE_PRIVADA_BASE64"')
        print()
        print("\033[93m  Si no tenes clave, genera una:\033[0m")
        print(f"    pyupdategit generate-keys --key-id {key_id}")
        sys.exit(1)
    return signing_key


def ensure_publish_keys_in_product_json(config: dict, config_file: Path) -> None:
    required_publish_keys = [
        "key_id",
        "manifest_url",
        "github_owner",
        "github_repo",
        "docs_repo",
        "updates_dir",
    ]

    missing = [key for key in required_publish_keys if key not in config]
    if not missing:
        return

    for key in missing:
        config[key] = ""

    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fail(
        "product.json actualizado con claves vacias faltantes: "
        + ", ".join(missing)
    )
    print("\033[93m  Rellena esos valores y vuelve a ejecutar release.py\033[0m")
    sys.exit(1)


def sync_product_version(config: dict, config_file: Path, release_version: str) -> None:
    current = config_text(config, "version")
    if current == release_version:
        return
    config["version"] = release_version
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if current:
        ok(f"product.json version actualizada: {current} -> {release_version}")
    else:
        ok(f"product.json version establecida: {release_version}")


def ensure_release_marker_in_zip(zip_path: Path, marker_name: str) -> None:
    marker_relative = Path("temp") / marker_name

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            marker_found = marker_relative.as_posix() in archive.namelist()
    except (zipfile.BadZipFile, OSError) as exc:
        fail(f"ZIP invalido o corrupto: {zip_path} ({exc})")
        sys.exit(1)

    if marker_found:
        ok(f"Marcador release presente en zip: {marker_relative.as_posix()}")
        return

    warn(f"Falta marcador en zip, se generara automaticamente: {marker_relative.as_posix()}")
    try:
        with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(marker_relative.as_posix(), "")
    except OSError as exc:
        fail(f"No se pudo escribir marcador en zip: {zip_path} ({exc})")
        sys.exit(1)

    ok(f"Marcador release agregado al zip: {marker_relative.as_posix()}")


def parse_strict_version(version: str, label: str) -> tuple[int, int, int]:
    raw = str(version).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", raw):
        fail(f"Version invalida en {label}: {version!r}. Formato obligatorio: X.Y.Z")
        sys.exit(1)
    major, minor, patch = raw.split(".")
    return int(major), int(minor), int(patch)


# ── Main ──────────────────────────────────────────────────────────


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    config_file = resolve_product_config(script_dir)
    release_file = script_dir / "release.json"
    project_root = config_file.parent.parent if config_file.parent.name == "c" else config_file.parent

    # ── Leer configuracion del proyecto ──────────────────────────
    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"product.json invalido: {exc}")
        sys.exit(1)

    if not isinstance(config, dict):
        fail("product.json invalido: el contenido raiz debe ser un objeto JSON")
        sys.exit(1)

    ensure_publish_keys_in_product_json(config, config_file)

    try:
        project_id = get_required_config(config, "project_id")
        nombre = config_text_first(config, "product_display_name", "product_name", "nombre", default=project_id)
        key_id = get_required_config(config, "key_id")
        manifest_url = get_required_config(config, "manifest_url")
        github_owner = get_required_config(config, "github_owner")
        github_repo = get_required_config(config, "github_repo")
        docs_repo = get_required_config(config, "docs_repo")
        updates_dir = get_required_config(config, "updates_dir")
        files_dir = child_config_path(config, "updates_dir", "files", explicit_key="files_dir")
    except KeyError as exc:
        fail(f"product.json incompleto: falta clave obligatoria {exc}")
        sys.exit(1)

    channel = config_text(config, "channel") or "stable"
    target = config_text(config, "target") or "win-x64"

    docs_repo_path = resolve_config_path(docs_repo, project_root)
    updates_dir_full = resolve_config_path(updates_dir, docs_repo_path)
    files_dir_full = resolve_config_path(files_dir, docs_repo_path)
    manifest_path = updates_dir_full / f"manifest-{channel}.json"
    github_repo_full = f"{github_owner}/{github_repo}"

    # ── 0) Pre-checks ────────────────────────────────────────────
    print(f"\n\033[93m=== pyupdategit Release — {nombre} ===\033[0m\n")
    info(f"Config  : {config_file}")
    errores: list[str] = []

    # pyupdategit
    try:
        r = run(["pyupdategit", "version"], check=False)
        if r.returncode != 0:
            raise FileNotFoundError
        ok(r.stdout.strip())
    except (FileNotFoundError, OSError):
        errores.append("pyupdategit no instalado. pipx install pyupdategit")

    # git
    try:
        r = run(["git", "--version"])
        ok(f"git: {r.stdout.strip()}")
    except (FileNotFoundError, OSError):
        errores.append("git no encontrado.")

    # gh
    try:
        r = run(["gh", "auth", "status"], check=False, capture=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "").strip())
        output = r.stdout + r.stderr
        if "not logged in" in output.lower():
            raise RuntimeError(output.strip())
        for line in output.splitlines():
            if "Logged in to" in line:
                ok(f"GitHub: {line.strip()}")
                break
        else:
            ok("GitHub: autenticado")
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        msg = str(exc).strip()
        if msg:
            errores.append(f"gh CLI no logueado o invalido: {msg}")
        else:
            errores.append("gh CLI no logueado. gh auth login")

    # release.json
    if not release_file.exists():
        errores.append(f"release.json no encontrado en: {script_dir}")
    else:
        ok("release.json encontrado")

    if errores:
        print("\n\033[91m=== ERRORES ===\033[0m")
        for e in errores:
            fail(e)
            print()
        print("\033[91mCorrige y vuelve a ejecutar.\033[0m")
        sys.exit(1)

    print()

    # ── 1) Leer release.json ─────────────────────────────────────
    try:
        rel = json.loads(release_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"release.json invalido: {exc}")
        sys.exit(1)

    version = str(rel.get("version", "")).strip()
    zip_name = validate_release_zip_name(str(rel.get("zip", "") if rel.get("zip") is not None else ""))
    notes = rel.get("notes", "")

    campos = []
    if not version:
        campos.append("version")
    if not zip_name:
        campos.append("zip")
    if campos:
        fail(f"release.json invalido: {', '.join(campos)}")
        sys.exit(1)

    parse_strict_version(version, "release.json")

    sync_product_version(config, config_file, version)

    rel_type_raw = rel.get("type")
    if rel_type_raw is not None:
        rel_type_raw = str(rel_type_raw).strip().lower()
        if rel_type_raw not in ("partial", "full"):
            fail("release.json invalido: type debe ser 'full' o omitirse")
            sys.exit(1)

    if rel_type_raw == "partial":
        fail("release.json invalido: type=partial ya no se admite; usa type=full o elimina type")
        print("\033[93m  Para Microsoft Store/Partner Center se publica siempre paquete completo.\033[0m")
        sys.exit(1)

    release_type = "full"

    info(f"Project : {project_id}")
    info(f"Version : {version}")
    if rel_type_raw:
        info(f"Tipo    : {release_type} (explicito en release.json)")
    else:
        info(f"Tipo    : {release_type} (por defecto)")
    info(f"Zip     : {zip_name}")
    if notes:
        info(f"Notas   : {notes}")
    print()

    print()

    # ── 2) Localizar el zip ──────────────────────────────────────
    zip_source = script_dir / zip_name
    ensure_zip_readable(zip_source)

    zip_size = zip_source.stat().st_size
    info(f"Tamaño  : {fmt_size(zip_size)}")
    print()

    load_signing_key(script_dir, key_id)

    marker_name = f"{project_id}.{version}"
    ensure_release_marker_in_zip(zip_source, marker_name)

    if not docs_repo_path.exists():
        fail(f"docs_repo no existe: {docs_repo_path}")
        sys.exit(1)

    # ── Limpieza de artefactos generados para mantener una sola release ───────────
    ensure_safe_updates_cleanup_path(updates_dir_full, docs_repo_path)
    clear_directory_contents(updates_dir_full, "updates_dir")
    if not files_dir_full.resolve().is_relative_to(updates_dir_full.resolve()):
        clear_directory_contents(files_dir_full, "files_dir")
    updates_dir_full.mkdir(parents=True, exist_ok=True)

    # ── 3) Publicar paquete completo ─────────────────────────────
    download_url = ""
    final_zip: Path = zip_source
    tag_name = f"v{version}"
    release_notes = notes or f"Release {version}"

    info(f"Modo FULL: subiendo {zip_name} a GitHub Releases...")
    try:
        r = run(
            [
                "gh",
                "release",
                "create",
                tag_name,
                f"{zip_source}#{zip_name}",
                "--repo",
                github_repo_full,
                "--title",
                f"{nombre} {version}",
                "--notes",
                release_notes,
            ],
            check=False,
        )
        if r.returncode != 0:
            fail(f"gh release create fallo:\n  {(r.stderr or r.stdout).strip()}")
            sys.exit(1)
    except (FileNotFoundError, OSError) as exc:
        fail(f"gh no encontrado: {exc}")
        sys.exit(1)

    download_url = f"https://github.com/{github_repo_full}/releases/download/{tag_name}/{zip_name}"
    ok(f"GitHub Release creado: {tag_name}")
    ok(f"URL descarga: {download_url}")

    print()

    # ── 4) Firmar manifest (siempre) ─────────────────────────────
    info("Firmando manifest...")

    final_zip = zip_source

    args_manifest = [
        "--project",
        project_id,
        "--channel",
        channel,
        "--version",
        version,
        "--key-id",
        key_id,
        "--signing-key-env",
        "UPDATE_PRIVATE_KEY",
        "--release-file",
        str(final_zip),
        "--release-type",
        release_type,
        "--release-target",
        target,
        "--release-url",
        download_url,
        "--output",
        str(manifest_path),
    ]

    if notes:
        args_manifest += ["--release-notes", notes]

    try:
        r = run(["pyupdategit", "build-manifest"] + args_manifest, check=False)
        if r.returncode != 0:
            fail(f"build_manifest fallo.\n  {(r.stderr or r.stdout).strip()}")
            sys.exit(1)
    except (FileNotFoundError, OSError) as exc:
        fail(f"pyupdategit no encontrado: {exc}")
        sys.exit(1)

    ok(f"Manifest firmado: manifest-{channel}.json")

    print()

    # ── 5) Deploy manifest con MkDocs ────────────────────────────
    try:
        r_mkdocs = run_mkdocs(["--version"], check=False, capture=True)
        if r_mkdocs.returncode != 0:
            r_mkdocs = run_mkdocs(["-V"], check=False, capture=True)
        if r_mkdocs.returncode != 0:
            details = (r_mkdocs.stderr or r_mkdocs.stdout or "").strip()
            fail("mkdocs esta instalado pero no responde correctamente a --version/-V")
            if details:
                print(f"\033[93m  Detalle: {details}\033[0m")
            print("\033[93m  El manifest fue creado pero no se ha publicado.\033[0m")
            sys.exit(1)
    except (FileNotFoundError, OSError):
        fail("mkdocs no esta instalado en este equipo.")
        print("\033[93m  El manifest fue creado pero no se ha publicado.\033[0m")
        print("\033[93m  pip install mkdocs-material\033[0m")
        sys.exit(1)

    if not docs_repo_path.exists():
        fail(f"docs_repo no existe: {docs_repo_path}")
        sys.exit(1)

    info("Desplegando con mkdocs gh-deploy --force...")
    print("[release] Ejecutando: mkdocs gh-deploy --force")
    site_dir = docs_repo_path / "site"
    try:
        r = run_mkdocs(["gh-deploy", "--force"], check=False, capture=True, cwd=docs_repo_path)
        output = (r.stdout or "") + (r.stderr or "")
        if output.strip():
            print(output)
        if r.returncode != 0:
            fail(f"mkdocs gh-deploy fallo.\n  {(r.stderr or r.stdout).strip()}")
            sys.exit(1)
        ok("Deploy completado")
    finally:
        if site_dir.exists() and site_dir.is_dir():
            shutil.rmtree(site_dir, ignore_errors=True)
            ok(f"site eliminado tras deploy: {site_dir}")

    # Cleanup old GitHub releases (keep only latest) — after everything else succeeded
    if release_type == "full":
        try:
            r = run(
                [
                    "gh",
                    "release",
                    "list",
                    "--repo",
                    github_repo_full,
                    "--json",
                    "tagName",
                    "--jq",
                    ".[].tagName",
                ],
                check=False,
            )
            if r.returncode == 0:
                for old_tag in r.stdout.strip().splitlines():
                    old_tag = old_tag.strip()
                    if old_tag and old_tag != f"v{version}":
                        info(f"Eliminando release vieja {old_tag} para mantener solo la ultima...")
                        run(
                            [
                                "gh",
                                "release",
                                "delete",
                                old_tag,
                                "--repo",
                                github_repo_full,
                                "--yes",
                            ],
                            check=False,
                        )
        except (FileNotFoundError, OSError):
            pass  # non-critical

    print()
    print(f"\033[92m=== Release {version} ({release_type}) completado ===\033[0m")
    print()
    print(f"\033[96m  Manifest:  {manifest_url}\033[0m")
    release_page_url = f"https://github.com/{github_repo_full}/releases/tag/v{version}"
    print(f"\033[96m  Release:   {release_page_url}\033[0m")
    print()

    info("Abriendo release en GitHub para continuar...")
    try:
        webbrowser.open(release_page_url)
    except Exception as exc:
        warn(f"No se pudo abrir el navegador automaticamente: {exc}")
        print(f"\033[93m  Abrila manualmente: {release_page_url}\033[0m")


if __name__ == "__main__":
    main()
