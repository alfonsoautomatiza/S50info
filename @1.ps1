# ================================
#  Build & empaquetado sage50bi
# ================================

$ErrorActionPreference = "Stop"   # Cualquier error de PowerShell detiene el script

# Ir siempre a la carpeta donde está el script
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

# Nombre base del proyecto
$nombreProyecto = "s50info"

Write-Host "== 1) Compilando extensión C (c\Capi.py) =="

python .\c\Capi.py build_ext --inplace
if ($LASTEXITCODE -ne 0) {
    Write-Error "La compilación de c\Capi.py ha fallado (código $LASTEXITCODE). Se detiene el script."
    exit $LASTEXITCODE
}

# -----------------------------
#  Copia de ficheros a .\exe
# -----------------------------
$carpetaExe = Join-Path $scriptRoot "exe"

if (-not (Test-Path $carpetaExe)) {
    New-Item -ItemType Directory -Path $carpetaExe | Out-Null
}

Copy-Item ".\${nombreProyecto}.*" -Destination $carpetaExe -Force
Copy-Item ".\c\version.txt"       -Destination $carpetaExe -Force
Copy-Item ".\img\hola.ico"        -Destination $carpetaExe -Force

# Cambiar al directorio "exe"
Set-Location $carpetaExe

# -----------------------------
#  PyInstaller
# -----------------------------
Write-Host "== 2) Ejecutando PyInstaller =="

pyinstaller --noconfirm --clean "$nombreProyecto.spec"
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller ha fallado (código $LASTEXITCODE). Se detiene el script."
    exit $LASTEXITCODE
}

# -----------------------------
#  Variables de rutas
# -----------------------------
$directorioBase = "dist\$nombreProyecto"   # desde .\exe
$zipDestino = "dist\$nombreProyecto.zip"

# -----------------------------
#  Robocopy con salida reducida
# -----------------------------
Write-Host "== 3) Copiando salida dist->$((Resolve-Path '..')) (Robocopy, salida mínima) =="

# Opciones para reducir ruido:
# /NFL  = No File List
# /NDL  = No Directory List
# /NJH  = No Job Header
# /NJS  = No Job Summary
# /NP   = No Progress
# /NS   = No Size
# /NC   = No Class
$rc = robocopy "dist\$nombreProyecto" "..\" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 `
    /NFL /NDL /NJH /NJS /NP /NS /NC

$exitRC = $LASTEXITCODE

# En Robocopy, 0-7 se consideran "éxito", >=8 es error
if ($exitRC -ge 8) {
    Write-Error "Robocopy ha devuelto un código de error $exitRC. Se detiene el script."
    exit $exitRC
}

# Si quieres SILENCIO TOTAL de Robocopy, puedes añadir:
# | Out-Null al final de la línea de robocopy

# -----------------------------
#  Comprimir con 7-Zip
# -----------------------------
Write-Host "== 4) Generando ZIP con 7-Zip =="

Push-Location $directorioBase  # .\exe\dist\sage50bi

& "C:\Program Files\7-Zip\7z.exe" a -tzip "..\$nombreProyecto.zip" "$nombreProyecto.exe" "_internal" `
    -mem=AES256 -mx=9 -r -y

if ($LASTEXITCODE -ne 0) {
    Write-Error "Error al crear el ZIP con 7-Zip (código $LASTEXITCODE)."
    Pop-Location
    exit $LASTEXITCODE
}

Pop-Location
Set-Location $scriptRoot

Write-Host "== Proceso completado correctamente. ZIP generado en: exe\$zipDestino =="
