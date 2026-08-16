"""
Build sage50bi executable.

Usage:
    uv sync --extra build
    uv run python c/build_exe.py
    uv run python c/build_exe.py --sync-only

Config:
    BUILD_MODE = "full"  # "full" = build completo, "pyd" = solo pyd a release (incremental), "zip" = build + zip

    Despues de build full, guarda .last_build con timestamp para sync incremental
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent

BUILD_MODE = "zip"  # "full" = build completo, "pyd" = solo pyd a release/_internal, "zip" = build + zip a release

PRODUCT_FILE = _SCRIPT_DIR / "product.json"
PYDOBJ_CONFIG_FILE = PROJECT_ROOT / "pydobj.toml"


@dataclass(frozen=True)
class ProductInfo:
    project_id: str
    product_name: str
    version: str
    company_name: str
    file_description: str
    internal_name: str
    original_filename: str
    product_display_name: str
    legal_copyright: str


@dataclass(frozen=True)
class ExternalModuleExpectation:
    module_name: str
    package_hints: tuple[str, ...] = ()


def read_product_json() -> dict:
    if not PRODUCT_FILE.exists():
        raise SystemExit(f"Definicion de producto no encontrada: {PRODUCT_FILE}")
    try:
        raw = json.loads(PRODUCT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON invalido en {PRODUCT_FILE}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SystemExit(f"JSON invalido en {PRODUCT_FILE}: el contenido raiz debe ser un objeto")
    return raw


def product_text(data: dict, key: str) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def product_text_first(data: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = product_text(data, key)
        if value:
            return value
    return default


def find_paired_entry_name(project_id: str) -> str:
    if (PROJECT_ROOT / f"{project_id}.py").exists() and (PROJECT_ROOT / f"{project_id}.spec").exists():
        return project_id

    paired = sorted(
        path.stem
        for path in PROJECT_ROOT.glob("*.spec")
        if (PROJECT_ROOT / f"{path.stem}.py").exists()
    )
    if len(paired) == 1:
        return paired[0]

    return project_id


def validate_version(version: str) -> None:
    raw_parts = [part.strip() for part in version.split(".")]
    if len(raw_parts) != 3 or any(not part.isdigit() for part in raw_parts):
        raise SystemExit(f"Version invalida en {PRODUCT_FILE}: {version!r}. Formato obligatorio: X.Y.Z")


def load_product_info() -> ProductInfo:
    data = read_product_json()

    project_id = product_text(data, "project_id")
    version = product_text(data, "version")
    required = {
        "project_id": project_id,
        "version": version,
        "company_name": product_text(data, "company_name"),
        "file_description": product_text(data, "file_description"),
        "legal_copyright": product_text(data, "legal_copyright"),
    }

    missing = sorted(key for key, value in required.items() if not value)
    if missing:
        raise SystemExit(f"Faltan claves obligatorias en {PRODUCT_FILE}: {', '.join(missing)}")

    validate_version(version)

    internal_name = product_text(data, "internal_name") or find_paired_entry_name(project_id)
    product_name = product_text(data, "product_name") or project_id
    product_display_name = product_text_first(
        data,
        "product_display_name",
        "product_name",
        default=project_id,
    )
    original_filename = product_text(data, "original_filename") or f"{project_id}.exe"

    expected_original_filename = f"{project_id}.exe"
    if original_filename != expected_original_filename:
        print(
            "[build] AVISO: original_filename no coincide con "
            f"project_id + '.exe' ({original_filename!r} != {expected_original_filename!r}). "
            "Se respeta el valor explicito de product.json."
        )

    return ProductInfo(
        project_id=project_id,
        product_name=product_name,
        version=version,
        company_name=required["company_name"],
        file_description=required["file_description"],
        internal_name=internal_name,
        original_filename=original_filename,
        product_display_name=product_display_name,
        legal_copyright=required["legal_copyright"],
    )


PRODUCT_INFO = load_product_info()

# Product identity vs common entry identity:
# - PROJECT_NAME is the shipped product id from c/product.json. It names the
#   final PyInstaller folder/exe, ZIPs, release manifests and updater markers.
# - ENTRY_NAME is the common code entry/spec. For this product family only
#   frames/ differs per centralita, so pydobj may legitimately show common
#   object paths such as D:\c\obj\centralita\... while the final product is
#   centralita_teamleader.
PROJECT_NAME = PRODUCT_INFO.project_id
ENTRY_NAME = PRODUCT_INFO.internal_name


def load_pydobj_build_config() -> dict[str, str]:
    if not PYDOBJ_CONFIG_FILE.exists():
        return {}

    try:
        data = tomllib.loads(PYDOBJ_CONFIG_FILE.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"TOML invalido en {PYDOBJ_CONFIG_FILE}: {exc}") from exc

    build = data.get("build", {})
    if not isinstance(build, dict):
        return {}
    return {key: str(value).strip() for key, value in build.items() if value is not None and str(value).strip()}


def load_pydobj_config() -> dict:
    if not PYDOBJ_CONFIG_FILE.exists():
        return {}

    try:
        return tomllib.loads(PYDOBJ_CONFIG_FILE.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"TOML invalido en {PYDOBJ_CONFIG_FILE}: {exc}") from exc


def resolve_config_path(raw_path: str) -> Path:
    value = raw_path.strip()
    if os.name != "nt":
        value = value.replace("\\", "/")
        if len(value) >= 3 and value[1:3] == ":/" and value[0].isalpha():
            value = f"/mnt/{value[0].lower()}/{value[3:]}"

    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


_pydobj_build_config = load_pydobj_build_config()
BUILD_BASE_DIR = resolve_config_path(_pydobj_build_config.get("build_dir", "D:/c")) / PROJECT_NAME

EXE_DIR = PROJECT_ROOT / "exe"
DIST_DIR = BUILD_BASE_DIR / "dist"
WORK_DIR = resolve_config_path("D:/temp") / PROJECT_NAME / "build"

MAIN_SCRIPT = PROJECT_ROOT / f"{ENTRY_NAME}.py"
SPEC_FILE = PROJECT_ROOT / f"{ENTRY_NAME}.spec"
VERSION_FILE = PROJECT_ROOT / "c" / "version.txt"
ICON_FILE = PROJECT_ROOT / "img" / "hola.ico"
INSTALLER_VERSION_FILE = PROJECT_ROOT / "instalador" / "version_auto.iss"
CHANNELS = ("release", "full")
RELEASE_DIR = PROJECT_ROOT / "release"
C_RELEASE_DIR = _SCRIPT_DIR / "RELEASE"
C_RELEASE_INTERNAL_DIR = C_RELEASE_DIR / "_internal"
RELEASE_MANIFEST_FILE = _SCRIPT_DIR / "RELEASE" / "release.json"
MSIX_BUILDER_FILE = PROJECT_ROOT / "msix" / "build_msix.py"

REQUIRED_MODULES = {
    "PyInstaller": "PyInstaller no esta disponible en este entorno. Instala con: uv sync --extra build",
}

PYDOBJ_CMD = shutil.which("pydobj")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build del ejecutable")
    parser.add_argument(
        "--channel",
        choices=CHANNELS,
        default="release",
        help="Canal para copiar marcador visual al distfinal.",
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Solo regenera derivados en c/ e instalador/, sin compilar.",
    )
    return parser.parse_args()


def print_step(message: str) -> None:
    print(f"== {message} ==")


def print_alert(message: str) -> None:
    print(f"\n\033[91m[ALERTA]\033[0m {message}")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    workdir = cwd or PROJECT_ROOT
    print("[build]", " ".join(str(part) for part in cmd))
    result = subprocess.run(cmd, cwd=str(workdir))
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def check_python_module(module_name: str, error_message: str) -> None:
    if importlib.util.find_spec(module_name) is None:
        raise SystemExit(error_message)


def check_dependencies() -> list[str]:
    missing = []

    for module_name, error_message in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(error_message)

    if not PYDOBJ_CMD:
        missing.append("pydobj no esta disponible. Instala con: pipx install pydobj")

    return missing


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"{label} no encontrado: {path}")


def remove_path_safe(path: Path) -> bool:
    if not path.exists():
        print(f"[build] No existe: {path}")
        return True

    for attempt in range(1, 6):
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"[build] Eliminado: {path}")
            return True
        except Exception:
            time.sleep(0.3 * attempt)

    print(f"[build] No se pudo eliminar la ruta (bloqueada): {path}")
    return False


def prepare_output_path(path: Path, label: str) -> Path:
    if not remove_path_safe(path):
        raise SystemExit(f"No se pudo preparar la carpeta {label}: {path}")
    return path


def copy_file_to_exe(path: Path) -> None:
    shutil.copy2(path, EXE_DIR / path.name)


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_version_parts(version: str) -> tuple[int, int, int, int]:
    validate_version(version)
    raw_parts = [part.strip() for part in version.split(".")]

    major, minor, patch = (int(part) for part in raw_parts)
    return major, minor, patch, 0


def version_text(parts: tuple[int, int, int, int]) -> str:
    return ".".join(str(part) for part in parts)


def render_version_resource(info: ProductInfo) -> str:
    parts = parse_version_parts(info.version)
    full_version = version_text(parts)
    return f"""# version.txt

# Generated by build_exe.py from c/product.json
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={parts},
    prodvers={parts},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '0C0A04B0',
        [
          StringStruct("CompanyName", {q(info.company_name)}),
          StringStruct("FileDescription", {q(info.file_description)}),
          StringStruct("FileVersion", {q(full_version)}),
          StringStruct("InternalName", {q(info.internal_name)}),
          StringStruct("LegalCopyright", {q(info.legal_copyright)}),
          StringStruct("OriginalFilename", {q(info.original_filename)}),
          StringStruct("ProductName", {q(info.product_display_name)}),
          StringStruct("ProductVersion", {q(full_version)})
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])])
  ]
)
"""


def sync_version_file(info: ProductInfo) -> None:
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(render_version_resource(info), encoding="utf-16")
    print(f"[build] Derivado actualizado: {VERSION_FILE}")


def sync_installer_version(info: ProductInfo) -> None:
    if not INSTALLER_VERSION_FILE.parent.exists():
        return
    content = (
        "; Generado automaticamente por build_exe.py desde c/product.json\n"
        f"#define MyAppVersion {q(info.version)}\n"
    )
    INSTALLER_VERSION_FILE.write_text(content, encoding="utf-8")
    print(f"[build] Derivado actualizado: {INSTALLER_VERSION_FILE}")


def sync_updater_marker(info: ProductInfo, channel: str) -> Path:
    temp_dir = PROJECT_ROOT / "c" / channel / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    marker_id = info.project_id
    prefix = f"{marker_id}."
    for item in temp_dir.iterdir():
        if item.is_file() and item.name.startswith(prefix):
            item.unlink()

    marker_path = temp_dir / f"{marker_id}.{info.version}"
    write_marker_file(marker_path, info, channel)
    print(f"[build] Marcador visual actualizado: {marker_path}")
    return marker_path


def build_marker_content(info: ProductInfo, channel: str) -> str:
    return (
        "\n".join(
            [
                f"product={info.product_name}",
                f"version={info.version}",
                f"channel={channel}",
            ]
        )
        + "\n"
    )


def write_marker_file(marker_path: Path, info: ProductInfo, channel: str) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(build_marker_content(info, channel), encoding="utf-8")


def create_zip_archive(source_path: Path) -> Path:
    C_RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    zip_name = f"{source_path.stem if source_path.is_file() else source_path.name}.zip"
    zip_path = C_RELEASE_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    zip_exclude_dirs, zip_exclude_files = load_zip_excludes()
    if source_path.is_file():
        scripts_dir = PROJECT_ROOT / "script"
        if not scripts_dir.is_dir() or not any(scripts_dir.iterdir()):
            raise SystemExit(
                f"Carpeta de scripts de ejemplo no disponible: {scripts_dir}. "
                "s50info la copia a %APPDATA%/s50info en el primer arranque."
            )
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(source_path, source_path.name)
            script_files = [
                item
                for item in sorted(scripts_dir.rglob("*"))
                if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc"
            ]
            for script_file in script_files:
                archive.write(script_file, Path("script") / script_file.relative_to(scripts_dir))
        created_count = 1 + len(script_files)
        skipped_count = 0
    else:
        created_count, skipped_count = make_filtered_zip_archive(
            source_path,
            zip_path,
            exclude_dirs=zip_exclude_dirs,
            exclude_files=zip_exclude_files,
        )
    print(f"[build] ZIP creado: {zip_path}")
    print(f"[build] ZIP incluidos: {created_count} archivo(s)")
    print(f"[build] ZIP excluidos: {skipped_count} archivo(s)")
    return zip_path


def sync_release_manifest_for_zip(info: ProductInfo, zip_path: Path) -> None:
    RELEASE_MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    release_data: dict[str, str] = {}
    if RELEASE_MANIFEST_FILE.exists():
        try:
            existing = json.loads(RELEASE_MANIFEST_FILE.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                release_data = {str(k): v for k, v in existing.items()}
        except json.JSONDecodeError as exc:
            raise SystemExit(f"JSON invalido en {RELEASE_MANIFEST_FILE}: {exc}") from exc

    release_data["version"] = info.version
    release_data["zip"] = zip_path.name
    version_parts = parse_version_parts(info.version)
    is_major_base_release = version_parts[1] == 0 and version_parts[2] == 0 and version_parts[3] == 0
    if is_major_base_release:
        release_data["type"] = "full"
    else:
        release_data.pop("type", None)
    release_data.setdefault("notes", "")

    RELEASE_MANIFEST_FILE.write_text(
        json.dumps(release_data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[build] release.json actualizado: {RELEASE_MANIFEST_FILE}")


def as_string_list(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SystemExit(f"Configuracion invalida: {label} debe ser una lista")
    return [str(item).strip().replace("\\", "/") for item in value if str(item).strip()]


def load_zip_excludes() -> tuple[list[str], list[str]]:
    data = load_pydobj_config()
    zip_config = data.get("zip", {})
    if zip_config is None:
        zip_config = {}
    if not isinstance(zip_config, dict):
        raise SystemExit("Configuracion invalida: [zip] debe ser una tabla")

    exclude_dirs = as_string_list(zip_config.get("exclude_dirs"), "zip.exclude_dirs")
    exclude_files = as_string_list(zip_config.get("exclude_files"), "zip.exclude_files")
    return exclude_dirs, exclude_files


def get_external_lib_expected_modules() -> list[ExternalModuleExpectation]:
    data = load_pydobj_config()
    external_libs = data.get("external_libs", {})
    if not isinstance(external_libs, dict):
        return []

    groups = external_libs.get("groups", [])
    if not isinstance(groups, list):
        return []

    expected: dict[str, set[str]] = {}
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            raise SystemExit(f"external_libs.groups #{index} invalido")

        verify_group = group.get("verify", True)
        if isinstance(verify_group, str):
            verify_group = verify_group.strip().lower() not in {"0", "false", "no", "off"}
        if not bool(verify_group):
            continue

        raw_files = group.get("files", [])
        if not isinstance(raw_files, list):
            raise SystemExit(f"external_libs.groups #{index}.files debe ser lista")

        src_dir_raw = str(group.get("dir", "")).strip()
        if not src_dir_raw:
            src_dir_raw = str(group.get("default_dir", "")).strip()
        src_dir = resolve_config_path(src_dir_raw) if src_dir_raw else None
        flatten_group = bool(group.get("flatten", False))

        package_hint = ""
        if src_dir_raw and not flatten_group:
            package_hint = Path(src_dir_raw.replace("\\", "/")).name.strip().lower()

        for pattern in raw_files:
            pattern_text = str(pattern).strip()
            if not pattern_text:
                continue

            if any(token in pattern_text for token in ("*", "?", "[")) and src_dir and src_dir.exists():
                for file_path in src_dir.glob(pattern_text):
                    if file_path.is_file() and file_path.suffix.lower() == ".py":
                        if file_path.stem != "__init__":
                            expected.setdefault(file_path.stem, set())
                            if package_hint:
                                expected[file_path.stem].add(package_hint)
                continue

            file_name = Path(pattern_text).name
            if file_name.lower().endswith(".py"):
                module_name = Path(file_name).stem
                if module_name != "__init__":
                    expected.setdefault(module_name, set())
                    if package_hint:
                        expected[module_name].add(package_hint)

    return [
        ExternalModuleExpectation(module_name=module, package_hints=tuple(sorted(hints)))
        for module, hints in sorted(expected.items())
    ]


def is_module_source_match(file_path: Path, module_name: str, package_hints: tuple[str, ...]) -> bool:
    suffix = file_path.suffix.lower()
    if suffix not in {".py", ".pyc"}:
        return False
    if file_path.stem.lower() != module_name.lower():
        return False

    if not package_hints:
        return True

    path_parts = {part.lower() for part in file_path.parts[:-1]}
    return any(hint in path_parts for hint in package_hints)


def contains_module_source_in_archive(archive_path: Path, module_name: str, package_hints: tuple[str, ...]) -> bool:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.namelist():
                member_path = Path(member)
                if is_module_source_match(member_path, module_name, package_hints):
                    return True
    except zipfile.BadZipFile:
        return False
    return False


def has_compiled_module(dist_files: list[Path], module_name: str, package_hints: tuple[str, ...]) -> bool:
    module_lower = module_name.lower()
    for path in dist_files:
        if path.suffix.lower() != ".pyd":
            continue

        stem_lower = path.stem.lower()
        if stem_lower != module_lower and not stem_lower.startswith(f"{module_lower}."):
            continue

        if package_hints:
            path_parts = {part.lower() for part in path.parts[:-1]}
            if not any(hint in path_parts for hint in package_hints):
                continue

        return True
    return False


def verify_external_libs_compiled(dist_target: Path) -> None:
    expectations = get_external_lib_expected_modules()
    if not expectations:
        print("[build] No hay modulos externos esperados para verificar")
        return

    missing_pyd: list[str] = []
    leaked_sources: list[str] = []
    dist_files = [path for path in dist_target.rglob("*") if path.is_file()]
    archives = [path for path in dist_files if path.suffix.lower() in {".zip", ".pyz"}]

    for expected in expectations:
        module = expected.module_name
        hints = expected.package_hints

        has_pyd = has_compiled_module(dist_files, module, hints)
        has_source_file = any(
            is_module_source_match(path, module, hints)
            for path in dist_files
        )
        has_source_archive = any(
            contains_module_source_in_archive(archive_path, module, hints)
            for archive_path in archives
        )

        if not has_pyd:
            missing_pyd.append(module)
            # Diagnostico detallado: mostrar que .pyd se encontraron (o no)
            module_lower = module.lower()
            pyd_candidates = [
                p for p in dist_files
                if p.suffix.lower() == ".pyd"
                and (p.stem.lower() == module_lower or p.stem.lower().startswith(f"{module_lower}."))
            ]
            if pyd_candidates:
                for p in pyd_candidates:
                    print(f"[build] DIAG {module}: .pyd encontrado pero hints no coinciden: {p} parts={p.parts[-3:]} hints={hints}")
            else:
                print(f"[build] DIAG {module}: no se encontro .pyd con nombre '{module}*' en {dist_target}")
        if has_source_file or has_source_archive:
            leaked_sources.append(module)

    if missing_pyd or leaked_sources:
        print_alert("Librerias externas no protegidas detectadas")
        if missing_pyd:
            print(f"[build] Faltan .pyd: {', '.join(missing_pyd)}")
        if leaked_sources:
            print(f"[build] Fuente detectada (.py/.pyc/zip): {', '.join(sorted(set(leaked_sources)))}")
        raise SystemExit("Build abortado por verificacion estricta de librerias externas")

    print(f"[build] Verificacion estricta OK: {len(expectations)} modulos externos solo compilados en .pyd")


def path_matches_any(path: str, name: str, patterns: list[str]) -> bool:
    normalized_path = path.replace("\\", "/")
    normalized_name = name.replace("\\", "/")
    return any(
        fnmatch.fnmatchcase(normalized_name, pattern)
        or fnmatch.fnmatchcase(normalized_path, pattern)
        or fnmatch.fnmatchcase(normalized_path, pattern.rstrip("/"))
        for pattern in patterns
    )


def should_exclude_from_zip(relative_path: Path, exclude_dirs: list[str], exclude_files: list[str]) -> bool:
    rel_posix = relative_path.as_posix()

    for parent in relative_path.parts[:-1]:
        if path_matches_any(parent, parent, exclude_dirs):
            return True

    parent_posix = relative_path.parent.as_posix()
    if parent_posix != "." and path_matches_any(parent_posix, relative_path.parent.name, exclude_dirs):
        return True

    return path_matches_any(rel_posix, relative_path.name, exclude_files)


def make_filtered_zip_archive(
    source_dir: Path,
    zip_path: Path,
    *,
    exclude_dirs: list[str],
    exclude_files: list[str],
) -> tuple[int, int]:
    created_count = 0
    skipped_count = 0

    print(f"[build] ZIP exclude_dirs: {exclude_dirs or '[]'}")
    print(f"[build] ZIP exclude_files: {exclude_files or '[]'}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for src in source_dir.rglob("*"):
            if not src.is_file():
                continue

            relative_path = src.relative_to(source_dir)
            if should_exclude_from_zip(relative_path, exclude_dirs, exclude_files):
                skipped_count += 1
                continue

            archive.write(src, relative_path.as_posix())
            created_count += 1

    return created_count, skipped_count


def sync_derived_files(info: ProductInfo) -> dict[str, Path]:
    sync_version_file(info)
    sync_installer_version(info)
    if BUILD_MODE == "zip":
        return {}
    return {channel: sync_updater_marker(info, channel) for channel in CHANNELS}


def stage_runtime_files() -> None:
    print_step("4) Copiando ficheos a exe")
    EXE_DIR.mkdir(parents=True, exist_ok=True)

    copy_file_to_exe(MAIN_SCRIPT)
    copy_file_to_exe(SPEC_FILE)
    copy_file_to_exe(VERSION_FILE)
    copy_file_to_exe(ICON_FILE)


def run_pydobj_only() -> None:
    print_step("3) Compilando pyd con pydobj")
    if not PYDOBJ_CMD:
        raise SystemExit("pydobj no esta disponible. Instala con: pipx install pydobj")
    run([PYDOBJ_CMD], cwd=PROJECT_ROOT)


def copy_extra_path(src: Path, dest: Path, dest_is_dir_hint: bool = False) -> int:
    if not src.exists():
        raise SystemExit(f"extra_copy src no encontrado: {src}")

    copied_count = 0

    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            if not item.is_file():
                continue
            target = dest / item.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied_count += 1
        return copied_count

    if dest.exists() and dest.is_dir():
        target = dest / src.name
    elif dest_is_dir_hint:
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / src.name
    else:
        target = dest

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    return 1


def ensure_path_inside(path: Path, parent: Path, label: str) -> Path:
    parent = parent.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(parent)
    except ValueError as exc:
        raise SystemExit(f"{label} fuera de target_dist: {path} -> {resolved}") from exc
    return resolved


def resolve_extra_copy_dest(raw_dest: str, target_dist: Path) -> Path:
    target_dist = target_dist.resolve()
    normalized = raw_dest.strip().replace("\\", "/")
    raw_is_absolute = Path(normalized).is_absolute() or (
        len(normalized) >= 3 and normalized[1:3] == ":/" and normalized[0].isalpha()
    )
    if not raw_is_absolute:
        return ensure_path_inside(target_dist / normalized, target_dist, "extra_copy dest")

    dest = resolve_config_path(raw_dest)

    if dest.is_absolute():
        try:
            dest.resolve().relative_to(target_dist)
            return dest.resolve()
        except ValueError:
            pass

    parts = [part for part in normalized.split("/") if part and part not in (".",)]
    for index in range(len(parts) - 1):
        if parts[index].lower() == "dist" and parts[index + 1].lower() == PROJECT_NAME.lower():
            relative_parts = parts[index + 2 :]
            if relative_parts:
                return ensure_path_inside(target_dist.joinpath(*relative_parts), target_dist, "extra_copy dest")

    raise SystemExit(f"extra_copy dest fuera de target_dist: {raw_dest} -> {dest}")


def apply_extra_copy_from_pydobj_config(target_dist: Path) -> None:
    data = load_pydobj_config()
    entries = data.get("extra_copy", [])
    if not entries:
        print("[build] No hay entradas [[extra_copy]] en pydobj.toml")
        return

    if not isinstance(entries, list):
        raise SystemExit("Configuracion invalida: [[extra_copy]] debe ser una lista de tablas")

    print_step("4) Aplicando extra_copy desde pydobj.toml")
    total_copied = 0

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise SystemExit(f"extra_copy #{index} invalido: debe ser una tabla")

        src_value = str(entry.get("src", "")).strip()
        dest_value = str(entry.get("dest", "")).strip()
        if not src_value or not dest_value:
            raise SystemExit(f"extra_copy #{index} invalido: requiere src y dest")

        src = resolve_config_path(src_value)
        dest = resolve_extra_copy_dest(dest_value, target_dist)
        copied = copy_extra_path(src, dest, dest_value.endswith(("/", "\\")))
        total_copied += copied
        print(f"[build] extra_copy #{index}: {copied} archivo(s) copiados de {src} a {dest}")

    print(f"[build] extra_copy completado: {total_copied} archivo(s) copiados")


LAST_BUILD_FILE = EXE_DIR / ".last_build"


def get_last_build_time() -> float:
    """Get timestamp of last build, or 0 if not exists."""
    EXE_DIR.mkdir(parents=True, exist_ok=True)
    if not LAST_BUILD_FILE.exists():
        print(f"[build] No existe .last_build en {EXE_DIR}, sync completo")
        return 0.0
    try:
        content = LAST_BUILD_FILE.read_text().strip()
        if not content:
            print("[build] .last_build vacio, sync completo")
            return 0.0
        result = float(content)
        print(f"[build] Ultimo build: {result}")
        return result
    except Exception as e:
        print(f"[build] Error leyendo .last_build: {e}, sync completo")
        return 0.0


def save_last_build_time() -> None:
    """Save current timestamp after each build (pyd or full)."""
    import time

    EXE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.time()
    LAST_BUILD_FILE.write_text(str(timestamp))
    print(f"[build] Timestamp de build guardado: {timestamp}")


def sync_changed_to_release(info: ProductInfo) -> Path:
    """Copy only changed files from exe/ to release/, excluding build/ and dist/.

    Si existe .last_build: copia archivos modificados DESPUÉS de ese timestamp.
    Si NO existe .last_build: no copia nada (0 archivos).
    """
    exclude_dirs = {"build", "dist", "__pycache__", ".git"}
    last_build = get_last_build_time()

    if last_build > 0:
        print(f"[build] Sync incremental desde: {last_build}")
    else:
        print("[build] Sin .last_build, no se copia nada a release/")
        return RELEASE_DIR

    copied_count = 0
    skipped_count = 0

    for src_root, _, files in os.walk(EXE_DIR):
        # Get relative path from EXE_DIR
        rel_root = Path(src_root).relative_to(EXE_DIR)

        # Skip excluded directories
        if any(part in exclude_dirs for part in rel_root.parts):
            continue

        for file in files:
            if file.endswith((".pyc", ".pyo")):
                continue

            src = Path(src_root) / file
            dest = RELEASE_DIR / rel_root / file

            # Create parent dirs if needed
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copiar solo si src es más nuevo que last_build
            src_mtime = src.stat().st_mtime
            if src_mtime > last_build:
                shutil.copy2(src, dest)
                copied_count += 1
            else:
                skipped_count += 1

    print(f"[build] {copied_count} archivos copiados a {RELEASE_DIR}")
    print(f"[build] {skipped_count} archivos sin cambios (saltados)")
    return RELEASE_DIR


def copy_changed_pyd(info: ProductInfo) -> Path:
    """Copy changed .pyd files from exe/ to c/RELEASE/_internal.

    El modo pyd prepara una release incremental de binarios compilados.
    Si existe .last_build, copia solo los .pyd modificados despues de ese timestamp.
    Si no existe .last_build, copia todos los .pyd para evitar una release vacia.
    La carpeta destino se limpia antes para que no queden .pyd antiguos de otra version.
    """
    last_build = get_last_build_time()
    source_files = sorted(path for path in EXE_DIR.rglob("*.pyd") if path.is_file())

    if not source_files:
        raise SystemExit(f"No se encontraron .pyd en {EXE_DIR}. Ejecuta primero un build/pydobj valido.")

    if C_RELEASE_INTERNAL_DIR.exists():
        shutil.rmtree(C_RELEASE_INTERNAL_DIR)
    C_RELEASE_INTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    skipped_count = 0

    if last_build > 0:
        print(f"[build] Copiando .pyd modificados desde timestamp: {last_build}")
    else:
        print("[build] Sin .last_build, se copiaran todos los .pyd a c/RELEASE/_internal")

    for src in source_files:
        if last_build > 0 and src.stat().st_mtime <= last_build:
            skipped_count += 1
            continue

        relative_path = src.relative_to(EXE_DIR)
        dest = C_RELEASE_INTERNAL_DIR / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied_count += 1
        print(f"[build] .pyd copiado: {relative_path} -> {dest}")

    if copied_count == 0:
        print("[build] No hay .pyd modificados para copiar")

    print(f"[build] {copied_count} .pyd copiado(s) a {C_RELEASE_INTERNAL_DIR}")
    print(f"[build] {skipped_count} .pyd sin cambios (saltados)")
    return C_RELEASE_INTERNAL_DIR


def run_pyinstaller(work_dir: Path, dist_dir: Path) -> None:
    print_step("5) Ejecutando PyInstaller")
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            SPEC_FILE.name,
            "--workpath",
            str(work_dir),
            "--distpath",
            str(dist_dir),
        ],
        cwd=EXE_DIR,
    )


def normalize_pyinstaller_output(dist_dir: Path, info: ProductInfo) -> Path:
    """Return the final onefile executable, renaming spec output if needed.

    ENTRY_NAME selects the entry script/spec. The packaged folder/exe identity is
    product.json project_id so release artifacts stay coherent.
    """
    target_exe = dist_dir / f"{info.project_id}.exe"
    if target_exe.exists():
        return target_exe

    exe_candidates = sorted(path for path in dist_dir.glob("*.exe") if path.is_file()) if dist_dir.exists() else []
    if len(exe_candidates) == 1:
        print(
            "[build] AVISO: el ejecutable generado no coincide con project_id "
            f"({exe_candidates[0].name!r} != {target_exe.name!r}). Se normaliza el nombre."
        )
        exe_candidates[0].rename(target_exe)

    ensure_exists(target_exe, "Ejecutable generado")
    return target_exe


def copy_channel_metadata_to_dist(
    target_dist: Path,
    marker_path: Path,
    info: ProductInfo,
    channel: str,
) -> None:
    print_step("6) Copiando metadatos visuales al dist")
    temp_dir = target_dist / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    if marker_path.exists():
        shutil.copy2(marker_path, temp_dir / marker_path.name)
        return

    print(f"[build] Marcador no encontrado, regenerando en dist: {marker_path.name}")
    write_marker_file(temp_dir / marker_path.name, info, channel)


def run_msix_builder(pyinstaller_output: Path) -> None:
    print_step("8) Generando MSIX para Microsoft Store")
    ensure_exists(MSIX_BUILDER_FILE, "Builder MSIX")
    run(
        [
            sys.executable,
            str(MSIX_BUILDER_FILE),
            "--build-root",
            str(pyinstaller_output),
        ],
        cwd=PROJECT_ROOT,
    )


def main() -> None:
    args = parse_args()

    print_step("1) Leyendo definicion canonica en c/product.json")
    product_info = PRODUCT_INFO

    print_step("2) Regenerando derivados de version")
    sync_derived_files(product_info)

    if args.sync_only:
        print("== Derivados sincronizados correctamente. No se ejecuto build. ==")
        return

    if BUILD_MODE == "pyd":
        print_step("3) Compilando pyd y copiando a c/RELEASE/_internal")
        run_pydobj_only()
        # En modo pyd: usar timestamp ANTERIOR (del último build) para copiar solo archivos nuevos
        # NO guardamos timestamp aquí - se guardará en el próximo build full
        copy_changed_pyd(product_info)
        print("== Proceso completado. Solo pyd copiados a c/RELEASE/_internal ==")
        return

    print_step("0) Comprobaciones previas")
    missing_deps = check_dependencies()
    if missing_deps:
        print("[build] Faltan dependencias:")
        for dep in missing_deps:
            print(f"  - {dep}")
        raise SystemExit("Build abortado: faltan dependencias")

    ensure_exists(MAIN_SCRIPT, "Script principal")
    ensure_exists(SPEC_FILE, "Spec")
    ensure_exists(ICON_FILE, "Icono")

    print_step("3) Limpieza de salida")
    dist_dir = prepare_output_path(DIST_DIR, "dist")
    work_dir = prepare_output_path(WORK_DIR, "build")

    run_pydobj_only()
    stage_runtime_files()
    run_pyinstaller(work_dir, dist_dir)

    target_exe = normalize_pyinstaller_output(dist_dir, product_info)

    print(f"[build] Onefile generado: {target_exe}")

    if BUILD_MODE != "zip":
        print_alert("BUILD_MODE no es zip: no se generara ZIP de release")

    print("[build] Verificacion de .pyd externos omitida: salida onefile sin archivos externos")

    if BUILD_MODE == "zip":
        zip_path = create_zip_archive(target_exe)
        sync_release_manifest_for_zip(product_info, zip_path)

    run_msix_builder(target_exe)

    # Guardar timestamp al final del build completo/zip, cuando todo ha terminado bien.
    save_last_build_time()

    print(
        f"== Proceso completado correctamente. Canal: {args.channel}. Salida en: {target_exe} =="
    )


if __name__ == "__main__":
    main()
