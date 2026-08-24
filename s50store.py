"""Puerta de actualización obligatoria desde Microsoft Store (instalaciones MSIX).

Módulo REUTILIZABLE en otros proyectos: sin dependencias fuera de la
librería estándar (rich es opcional para el formato del mensaje). Copia este
fichero al raíz de tu proyecto y llámalo desde tu punto de entrada:

    import s50store

    if s50store.puerta_update_obligatorio(
        nombre_app="miapp", store_product_id="9NXXXXXXXXXXXX"
    ):
        raise SystemExit(1)  # el cliente debe actualizar en la Store y relanzar

Cómo decide: compara la versión publicada en el catálogo público de la Store
(DisplayCatalog, el mismo que usa winget) con la versión instalada del
paquete MSIX. Requisitos: distribución MSIX; en instalaciones sin identidad
de paquete (ZIP, instalador clásico) la puerta no actúa.

Política fail-open: únicamente un ``True`` definitivo bloquea — sin red,
timeout, catálogo caído o versiones ilegibles dejan continuar al cliente.
"""

import json
import logging
import re
import subprocess
import sys
import urllib.error
from urllib import request as urlrequest

_logger = logging.getLogger(__name__)

STORE_UPDATES_URI = "ms-windows-store://downloadsandupdates"
DISPLAYCATALOG_URL = "https://displaycatalog.mp.microsoft.com/v7.0/products"

_VERSION_EN_FULL_NAME = re.compile(r"_([0-9]+(?:\.[0-9]+)+)_")
_MARKUP = re.compile(r"\[/?[^\]]+\]")
_FAMILY_VALIDA = re.compile(r"^[A-Za-z0-9_.\-]+$")

# PowerShell 5.1 (powershell.exe, nunca pwsh: PowerShell 7 no expone WinRT).
# Instalación silenciosa: UpdateAppByPackageFamilyNameAsync dispara el update
# del paquete y devuelve un AppInstallItem cuyo estado se sondea hasta que
# completa o se agota la espera. Verificado sin E_ACCESSDENIED bajo identidad
# de paquete (a diferencia de SearchForAllUpdatesAsync).
_DISPARO_PS = """
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $null = [Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallItem,Windows.ApplicationModel.Store.Preview.InstallControl,ContentType=WindowsRuntime]
  $null = [Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager,Windows.ApplicationModel.Store.Preview.InstallControl,ContentType=WindowsRuntime]
  $mgr = New-Object Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager
  $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  } | Select-Object -First 1)
  $mi = [Windows.ApplicationModel.Store.Preview.InstallControl.AppInstallManager].GetMethods() |
    Where-Object { $_.Name -eq 'UpdateAppByPackageFamilyNameAsync' } | Select-Object -First 1
  $elem = $mi.ReturnType.GetGenericArguments()[0]
  $op = $mgr.UpdateAppByPackageFamilyNameAsync('__FAMILY__')
  $task = $asTaskGeneric.MakeGenericMethod($elem).Invoke($null, @($op))
  if (-not $task.Wait(20000)) { Write-Output 'Timeout'; exit }
  $item = $task.Result
  if ($null -eq $item) { Write-Output 'SIN_UPDATE'; exit }
  $limite = (Get-Date).AddSeconds(__WAIT__)
  while ((Get-Date) -lt $limite) {
    $estado = $item.GetCurrentStatus().InstallState.ToString()
    if ($estado -eq 'Completed') { Write-Output 'COMPLETADA'; exit }
    if ($estado -eq 'Error') { Write-Output 'ERROR_ESTADO'; exit }
    Start-Sleep -Seconds 2
  }
  Write-Output 'EN_CURSO'
} catch {
  Write-Output 'Error'
}
"""


def _ejecutar_ps(script: str, timeout: float):
    """Ejecuta un script PowerShell y devuelve (rc, salida); None si no corre."""
    try:
        resultado = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        _logger.info("store: PowerShell no disponible: %s", exc)
        return None
    return resultado.returncode, (resultado.stdout or "").strip()


def package_full_name() -> str | None:
    """PackageFullName del paquete Store, o None si no hay identidad."""
    if sys.platform != "win32":
        return None
    import ctypes

    kernel32 = ctypes.windll.kernel32
    size = ctypes.c_uint32(0)
    rc = kernel32.GetCurrentPackageFullName(ctypes.byref(size), None)
    if rc == 15700:  # APPMODEL_ERROR_NO_PACKAGE: instalación no MSIX
        return None
    if rc != 122:  # ERROR_INSUFFICIENT_BUFFER esperado en el primer paso
        return None
    buffer = ctypes.create_unicode_buffer(size.value)
    rc = kernel32.GetCurrentPackageFullName(ctypes.byref(size), buffer)
    return buffer.value if rc == 0 and buffer.value else None


def version_de_full_name(full_name: str) -> tuple[int, ...] | None:
    """Extrae la versión de un PackageFullName tipo app_2.2.1.0_arch__hash."""
    match = _VERSION_EN_FULL_NAME.search(full_name or "")
    if not match:
        return None
    try:
        return tuple(int(parte) for parte in match.group(1).split("."))
    except ValueError:
        return None


def family_de_full_name(full_name: str) -> str:
    """Deriva el PackageFamilyName de un PackageFullName.

    InfoMSD.s50info_2.2.1.0_neutral__xjc995t8xskrw ->
    InfoMSD.s50info_xjc995t8xskrw
    """
    if "__" not in (full_name or ""):
        return ""
    prefijo, _, hash_publicador = full_name.partition("__")
    nombre = prefijo.split("_")[0]
    if not nombre or not hash_publicador:
        return ""
    return f"{nombre}_{hash_publicador}"


def version_tienda(product_id: str, timeout: float = 8.0) -> tuple[int, ...] | None:
    """Versión publicada en la Store para product_id (9N...); None si falla."""
    if not product_id:
        return None
    url = f"{DISPLAYCATALOG_URL}?bigIds={product_id}&market=ES&languages=es-es"
    try:
        peticion = urlrequest.Request(url, headers={"Accept": "application/json"})
        with urlrequest.urlopen(peticion, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read())
    except (OSError, urllib.error.URLError, ValueError) as exc:
        _logger.info("store: DisplayCatalog no disponible: %s", exc)
        return None

    if not isinstance(datos, dict):
        _logger.info("store: respuesta DisplayCatalog inesperada (no es objeto)")
        return None

    # Formas malformadas (tipos inesperados en cualquier nivel) -> fail-open.
    versiones = []
    productos = datos.get("Products", [])
    if not isinstance(productos, list):
        return None
    for producto in productos:
        if not isinstance(producto, dict):
            continue
        skus = producto.get("DisplaySkuAvailabilities", [])
        if not isinstance(skus, list):
            continue
        for sku in skus:
            if not isinstance(sku, dict):
                continue
            sku_propio = sku.get("Sku")
            if not isinstance(sku_propio, dict):
                continue
            propiedades = sku_propio.get("Properties")
            if not isinstance(propiedades, dict):
                continue
            paquetes = propiedades.get("Packages", [])
            if not isinstance(paquetes, list):
                continue
            for paquete in paquetes:
                if not isinstance(paquete, dict):
                    continue
                version = version_de_full_name(paquete.get("PackageFullName", ""))
                if version:
                    versiones.append(version)
    return max(versiones) if versiones else None


def disparar_actualizacion_silenciosa(
    family_name: str, timeout_espera: float = 90.0
) -> str | None:
    """Dispara la instalación silenciosa del update y espera acotadamente.

    Devuelve 'completada', 'en_curso', 'sin_update' o None si algo falló.
    """
    if not family_name or not _FAMILY_VALIDA.match(family_name):
        return None
    script = _DISPARO_PS.replace("__FAMILY__", family_name).replace(
        "__WAIT__", str(int(timeout_espera))
    )
    ejecucion = _ejecutar_ps(script, timeout=20 + timeout_espera + 10)
    if ejecucion is None or ejecucion[0] != 0:
        return None
    return {
        "COMPLETADA": "completada",
        "EN_CURSO": "en_curso",
        "SIN_UPDATE": "sin_update",
    }.get(ejecucion[1])


def abrir_tienda(uri: str = STORE_UPDATES_URI) -> None:
    """Abre la ventana Descargas y actualizaciones de Microsoft Store."""
    startfile = getattr(__import__("os"), "startfile", None)
    if sys.platform == "win32" and startfile is not None:
        try:
            startfile(uri)
            return
        except OSError:
            _logger.warning("store: os.startfile falló para %s; pruebo webbrowser", uri)
    import webbrowser

    try:
        webbrowser.open(uri)
    except Exception as exc:  # noqa: BLE001 - webbrowser.Error varía por plataforma
        _logger.warning("store: no se pudo abrir %s: %s", uri, exc)


def _imprimir(texto: str) -> None:
    try:
        from rich import print as rprint

        rprint(texto)
    except ImportError:
        print(_MARKUP.sub("", texto))


def puerta_update_obligatorio(
    nombre_app: str | None = None,
    store_product_id: str | None = None,
    timeout_espera: float = 90.0,
) -> bool:
    """Puerta de actualización silenciosa-obligatoria. True = bloquear y salir.

    Flujo cuando la Store tiene versión estrictamente mayor que la instalada:
    1. Dispara la instalación en segundo plano (sin abrir la Store).
    2. Si completa dentro del timeout -> avisa y deja continuar ya actualizado.
    3. Si sigue descargando -> bloquea pidiendo reintentar en un momento.
    4. Si la Store aún no sirve la versión (rollout) o falla el disparo:
       avisa, abre la ventana de actualizaciones y continúa (fail-open,
       nunca bloquea).
    """
    if not store_product_id:
        return False
    full_name = package_full_name() or ""
    instalada = version_de_full_name(full_name)
    if instalada is None:
        return False
    tienda = version_tienda(store_product_id)
    if tienda is None or tienda <= instalada:
        return False

    app = nombre_app or "la aplicación"
    version_nueva = ".".join(str(p) for p in tienda)
    resultado = disparar_actualizacion_silenciosa(
        family_de_full_name(full_name), timeout_espera
    )

    if resultado == "completada":
        _imprimir(
            f"[bold green]{app} se ha actualizado a la versión {version_nueva} "
            "en segundo plano.[/bold green]"
        )
        return False
    if resultado == "sin_update":
        # Rollout: DisplayCatalog la anuncia pero la Store aún no la sirve.
        _imprimir(
            f"[grey70]Hay una versión nueva ({version_nueva}) que todavía no "
            f"está disponible para tu equipo; continúa con la actual.[/grey70]"
        )
        return False
    if resultado == "en_curso":
        _imprimir(
            f"[bold yellow]{app} se está actualizando a la versión {version_nueva} "
            "en segundo plano.[/bold yellow]"
        )
        _imprimir("[yellow]Espera un momento y vuelve a ejecutar el programa.[/yellow]")
        return True

    # Último recurso: fallo del disparo (PowerShell bloqueado, WinRT, timeout).
    # Fail-open: avisa, abre la Store y deja continuar con la versión actual.
    _imprimir(
        f"[bold yellow]{app} no se pudo actualizar automáticamente; "
        "se abrió la Store. Continúa con la versión actual.[/bold yellow]"
    )
    abrir_tienda()
    return False
