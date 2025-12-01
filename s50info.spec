# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

codigo_modules = []
apisage50_modules = []
# Recopilar los archivos .pyd compilados de las carpetas exe/codigo y exe/apiSage50
binaries = []


# Agregar archivos .pyd de apiSage50, incluyendo subdirectorios
apisage50_pyd_dir = os.path.join(SPECPATH, "apiSage50")
if os.path.exists(apisage50_pyd_dir):
    for root, _, files in os.walk(apisage50_pyd_dir):
        for file in files:
            if file.endswith(".pyd"):
                src = os.path.join(root, file)
                # Determinar la ruta de destino relativa al directorio raíz de PyInstaller (SPECPATH)
                # Esto preservará la estructura de directorios dentro del paquete apiSage50
                dest_folder = os.path.relpath(root, SPECPATH)
                binaries.append((src, dest_folder))

# Asegura que PyInstaller analice los módulos usando la raíz del proyecto
project_root = os.path.abspath(os.path.join(SPECPATH, os.pardir))
external_paths = [
    os.path.abspath(os.path.join(project_root, "..", "@api", "mislibrerias")),
    os.path.abspath(os.path.join(project_root, "..", "@api", "api_sage50")),
]
external_paths = [p for p in external_paths if os.path.isdir(p)]
block_cipher = None


# Configuración del análisis del script principal
a = Analysis(
    ['s50info.py'],
    pathex=[project_root] + external_paths,
    binaries=binaries,
    datas=[],
    hiddenimports=['json', 'configparser',"exportador_resultados","pandas","openpyxl",
                   'xml.etree.ElementTree',
                   'webbrowser', 'pyodbc', 'libwertyconfig', 'libwertylog', 'libwertymail',
                   'cryptography.fernet', 'httpx', 'psutil',"cryptography.hazmat.bindings._rust",
                   'clr', 'http.server', 'requests_oauthlib', 'email.mime', 'email.mime.text',
                   'email.mime.multipart', 'email.mime.application', 'markdown',
                   'uuid', 'logging.handlers', 'PySimpleGUI', 'libsage50'] + apisage50_modules,
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

# Genera el ejecutable como carpeta (no en modo onefile)
exe = EXE(
    pyz,
    a.scripts,
    [],  # Sin binarios aquí, se guardan por separado
    exclude_binaries=True,
    name='s50info',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='hola.ico',
    version='version.txt',
)

# Recopila archivos necesarios en una carpeta COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='s50info'
)
