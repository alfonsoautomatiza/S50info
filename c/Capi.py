import glob
import os

from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

# Directorio base donde se encuentran los módulos a compilar
base_dir = r"c:\py\@produxion"

# Construir rutas de manera portable
main_dir = os.path.join(base_dir, "@SAGE50", "s50info")
api_dir = os.path.join(base_dir, "@api")
mislibrerias_dir = os.path.join(api_dir, "mislibrerias")

extensions = []

# 1. Root files
extensions.append(Extension("s50info", [os.path.join(main_dir, "s50info.py")]))

# 2. Mislibrerias
lib_files = [
    "libwertyconfig.py",
    "libwertyupdate.py",
    "libwertylog.py",
    "libwertymail.py",
    "libsage50.py",
    "libwertyficheros.py",
    "libwertygoogle.py",
]
for f in lib_files:
    path = os.path.join(mislibrerias_dir, f)
    name = os.path.splitext(f)[0]
    extensions.append(Extension(name, [path]))

# # 3. Codigo
# codigo_patterns = ["proceso*.py", "import*.py", "gui*.py", "data*.py", "config*.py"]
# for pattern in codigo_patterns:
#     for path in glob.glob(os.path.join(main_dir, "codigo", pattern)):
#         filename = os.path.basename(path)
#         name = os.path.splitext(filename)[0]
#         extensions.append(Extension(f"codigo.{name}", [path]))

 # 4. apiSage50
api_sage50_dir = r"c:/PY/@produxion/@api/mislibrerias/apiSage50"
base_api_dir = os.path.dirname(api_sage50_dir)  # C:\py\@produxion\@api\api_sage50

for root, dirs, files in os.walk(api_sage50_dir):
    for file in files:
        if file.endswith(".py"):
            abs_path = os.path.join(root, file)
            # Calculate module name relative to the parent of apiSage50 directory
            # e.g. apiSage50/helper/foo.py -> apiSage50.helper.foo
            rel_path = os.path.relpath(abs_path, base_api_dir)
            module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
            extensions.append(Extension(module_name, [abs_path]))

destino_carpeta_c = "e:\\c"
exe_dir = "exe"

# Asegurar que el directorio exe existe (setup lo creará, pero por si acaso)
os.makedirs(exe_dir, exist_ok=True)

setup(
    name="Lib Modulos",
    ext_modules=cythonize(
        extensions,
        build_dir=destino_carpeta_c,
        compiler_directives={"binding": False, "language_level": "3"},
        annotate=False,
    ),
    script_args=["build_ext", "--build-lib", exe_dir],
    packages=find_packages(
        exclude=[
            "dll",
            "exe",
            "img",
            "OLD",
            "json",
            "temp",
            "ADDON",
            "hooks",
            "Local",
            "backup",
            "locale",
            "instalador",
            "plantillas",
        ]
    ),
    build_temp=destino_carpeta_c,
)

# Eliminar archivos .c en el directorio actual si quedaron (aunque build_dir debería manejarlo)
for file in glob.glob("*.c"):
    os.remove(file)

# Imprimir resultado (nombres de módulos raíz)
root_modules = ["xls2sage50"] + [os.path.splitext(f)[0] for f in lib_files]
resultado = "','".join(root_modules)
