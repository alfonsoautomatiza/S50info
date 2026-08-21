"""Puerta de actualización obligatoria desde Microsoft Store (instalaciones MSIX).

Módulo REUTILIZABLE en otros proyectos: sin dependencias fuera de la
librería estándar (rich es opcional para el formato del mensaje). Copia este
fichero al raíz de tu proyecto y llámalo desde tu punto de entrada:

    import s50store

    if s50store.puerta_update_obligatorio(nombre_app="miapp"):
        raise SystemExit(1)  # el cliente debe actualizar en la Store y relanzar

Requisitos: la app debe distribuirse como MSIX (Microsoft Store). En
instalaciones sin identidad de paquete (ZIP, instalador clásico) la puerta
no actúa. Politica fail-open: unicamente un ``True`` definitivo de la Store
bloquea; timeout, sin red o error dejan continuar al cliente.
"""

import logging
import re
import subprocess
import sys

_logger = logging.getLogger(__name__)

STORE_UPDATES_URI = "ms-windows-store://downloadsandupdates"

_FAMILY_VALIDA = re.compile(r"^[A-Za-z0-9_.\-]+$")

# PowerShell 5.1 (powershell.exe, nunca pwsh: PowerShell 7 no expone WinRT).
# Consulta a la Store: GetIsAppUpdateAvailableAsync recibe el package family
# name y devuelve IAsyncOperation[bool]. El baile de AsTask convierte la
# operacion WinRT a Task para poder esperarla con timeout.
_CONSULTA_PS = """
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $null = [Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager,Windows.ApplicationModel.Store.Preview.InstallControl,ContentType=WindowsRuntime]
  $mgr = New-Object Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager
  $op = $mgr.GetIsAppUpdateAvailableAsync('__FAMILY__')
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  } | Select-Object -First 1)
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
    if rc == 15700:  # APPMODEL_ERROR_NO_PACKAGE: instalacion no MSIX
        return None
    if rc != 122:  # ERROR_INSUFFICIENT_BUFFER esperado en el primer paso
        return None
    buffer = ctypes.create_unicode_buffer(size.value)
    rc = kernel32.GetCurrentPackageFamilyName(ctypes.byref(size), buffer)
    return buffer.value if rc == 0 and buffer.value else None


def actualizacion_disponible(family_name: str | None = None) -> bool | None:
    """True/False segun la Store; None si no se pudo consultar (fail-open)."""
    family_name = family_name or package_family_name()
    if not family_name or not _FAMILY_VALIDA.match(family_name):
        return None
    try:
        resultado = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                _CONSULTA_PS.replace("__FAMILY__", family_name),
            ],
            capture_output=True,
            text=True,
            timeout=25,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        _logger.info("store: consulta no disponible: %s", exc)
        return None
    salida = (resultado.stdout or "").strip()
    if resultado.returncode == 0 and salida == "True":
        return True
    if resultado.returncode == 0 and salida == "False":
        return False
    _logger.info(
        "store: respuesta no concluyente (rc=%s, out=%r)",
        resultado.returncode,
        salida[:80],
    )
    return None


def abrir_tienda(uri: str = STORE_UPDATES_URI) -> None:
    """Abre la ventana Descargas y actualizaciones de Microsoft Store."""
    startfile = getattr(__import__("os"), "startfile", None)
    if sys.platform == "win32" and startfile is not None:
        try:
            startfile(uri)
            return
        except OSError:
            _logger.warning("store: os.startfile fallo para %s; pruebo webbrowser", uri)
    import webbrowser

    try:
        webbrowser.open(uri)
    except Exception as exc:  # noqa: BLE001 - webbrowser.Error varia por plataforma
        _logger.warning("store: no se pudo abrir %s: %s", uri, exc)


def _imprimir(texto: str) -> None:
    try:
        from rich import print as rprint

        rprint(texto)
    except ImportError:
        import re as _re

        print(_re.sub(r"\[/?[^\]]+\]", "", texto))


def puerta_update_obligatorio(nombre_app: str | None = None) -> bool:
    """Puerta de actualizacion obligatoria. True = bloquear y salir.

    Solo bloquea ante un ``True`` definitivo de la Store (fail-open en todo
    lo demas). Al bloquear ya ha impreso el aviso y abierto la ventana de
    actualizaciones de la Store; el llamador debe terminar el proceso.
    """
    family = package_family_name()
    if not family:
        return False
    if actualizacion_disponible(family) is not True:
        return False

    app = nombre_app or "la aplicación"
    _imprimir(
        f"[bold yellow]Hay una actualización obligatoria de {app} disponible "
        "en Microsoft Store.[/bold yellow]"
    )
    _imprimir(
        f"Se abrió la ventana de actualizaciones de la Store: actualiza "
        f"{app} y vuelve a ejecutar el programa."
    )
    _imprimir("[grey70]No puedes continuar con esta versión.[/grey70]")
    abrir_tienda()
    return True
