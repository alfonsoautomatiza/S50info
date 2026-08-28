# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from importlib.metadata import PackageNotFoundError

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


spec_root = Path(SPECPATH).resolve()
project_root = spec_root.parent
block_cipher = None


def existing_paths(*paths):
    return [str(path) for path in paths if path.is_dir()]


def collect_local_binaries(base_dir):
    binaries = []
    for pattern in ("*.pyd", "*.dll"):
        for src in base_dir.rglob(pattern):
            dest = "." if src.parent == base_dir else os.path.relpath(src.parent, base_dir)
            binaries.append((str(src), dest))
    return binaries


def collect_local_datas(base_dir, project_dir):
    datas = []

    # config.ini / agent.ini NO se empaquetan: se crean en runtime cuando la
    # app detecta un SAGE50 instalado. Empaquetarlos metia datos de desarrollo
    # en el instalador y rompia el primer arranque en MSIX (carpeta read-only).
    script_dir = project_dir / "script"
    if script_dir.is_dir():
        for src in script_dir.rglob("*.py"):
            dest = os.path.relpath(src.parent, project_dir)
            datas.append((str(src), dest))

    return datas


def safe_copy_metadata(package_name):
    try:
        return copy_metadata(package_name)
    except PackageNotFoundError:
        return []


def safe_collect_data_files(package_name, include_py_files=False):
    try:
        return collect_data_files(package_name, include_py_files=include_py_files)
    except Exception:
        return []


def safe_collect_submodules(package_name, **kwargs):
    try:
        return collect_submodules(package_name, **kwargs)
    except Exception:
        return []


external_paths = existing_paths(
    Path("P:/mislibrerias"),
    Path("P:/api/pysage50e"),
)

binaries = collect_local_binaries(spec_root)

datas = collect_local_datas(spec_root, project_root)
for package in ("openpyxl", "markdown", "pysage50e", "PySimpleGUI", "nacl", "polars"):
    datas += safe_collect_data_files(package, include_py_files=False)

hiddenimports = [
    "_cffi_backend",
    "_elementpath",
    "cffi",
    "cffi.api",
    "cffi.vengine_cpy",
    "configparser",
    "cryptography.fernet",
    "cryptography.hazmat.bindings._rust",
    "dotenv",
    "email.mime.application",
    "email.mime.multipart",
    "email.mime.text",
    "http.server",
    "html",
    "html.entities",
    "html.parser",
    "httpx",
    "json",
    "libupdatemsix",
    "libwertyconfig",
    "libwertyemail",
    "libwertylog",
    "libwertymail",
    "wertyfeedback",
    "logging.handlers",
    "lxml._elementpath",
    "lxml.etree",
    "markdown",
    "nacl",
    "nacl.bindings",
    "nacl.encoding",
    "nacl.exceptions",
    "nacl.signing",
    "openpyxl",
    "polars",
    "psutil",
    "pyodbc",
    "PySimpleGUI",
    "PySimpleGUI.PySimpleGUI",
    "rich",
    "s50exportador_resultados",
    "s50proceso",
    "s50script",
    "s50setup",
    "sqlparse",
    "typer",
    "uuid",
    "webbrowser",
    "xml.etree.ElementTree",
    "xml.etree.ElementPath",
    "pynacl",
]

for package in ("pysage50e", "rich", "typer", "openpyxl", "lxml", "PySimpleGUI", "nacl"):
    hiddenimports += safe_collect_submodules(package)

hiddenimports += safe_collect_submodules(
    "polars",
    filter=lambda name: not name.startswith("polars.testing"),
)

for package in (
    "markdown",
    "python-docx",
    "pysage50e",
    "rich",
    "typer",
    "PyNaCl",
    "pynacl",
    "PySimpleGUI",
    "pysimplegui-4-foss",
    "polars",
):
    datas += safe_copy_metadata(package)


# Configuración del análisis del script principal
a = Analysis(
    ['s50info.py'],
    pathex=[str(project_root)] + external_paths,
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Genera un unico ejecutable onefile.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name='s50info',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon='hola.ico',
    version='version.txt',
)
