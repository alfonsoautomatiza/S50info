
python c\Capi.py build_ext --inplace

# Cambiar al directorio "exe"

Copy-Item -Path ".\s50info.*" -Destination ".\exe\" -Force

Set-Location -Path "exe"
# Ejecutar PyInstaller con el archivo de especificaciones
pyinstaller s50info.spec --noconfirm


# Nombre base del proyecto
$nombreProyecto = "s50info"

# Ruta base de trabajo (donde están los archivos a comprimir)
$directorioBase = "dist\${nombreProyecto}_dist"

# Ruta final del ZIP
$zipDestino = "dist\$nombreProyecto.zip"

# Contraseña
# $clave = "123"

# Cambiar al directorio base para evitar incluir carpetas en el ZIP
Push-Location $directorioBase

# Comprimir el ejecutable y el contenido de _internal en la raíz del ZIP
& "C:\Program Files\7-Zip\7z.exe" a -tzip "..\$nombreProyecto.zip" "$nombreProyecto.exe" "_internal"  -mem=AES256 -mx=9 -r -y




# Volver al directorio original
Pop-Location
Set-Location -Path ".."
