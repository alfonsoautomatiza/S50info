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
import sys
import urllib.error
from urllib import request as urlrequest

_logger = logging.getLogger(__name__)

STORE_UPDATES_URI = "ms-windows-store://downloadsandupdates"
DISPLAYCATALOG_URL = "https://displaycatalog.mp.microsoft.com/v7.0/products"

_VERSION_EN_FULL_NAME = re.compile(r"_([0-9]+(?:\.[0-9]+)+)_")
_MARKUP = re.compile(r"\[/?[^\]]+\]")


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

    versiones = []
    for producto in datos.get("Products", []):
        for sku in producto.get("DisplaySkuAvailabilities", []):
            for paquete in sku.get("Sku", {}).get("Properties", {}).get("Packages", []):
                version = version_de_full_name(paquete.get("PackageFullName", ""))
                if version:
                    versiones.append(version)
    return max(versiones) if versiones else None


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


def puerta_update_obligatorio(nombre_app: str | None = None, store_product_id: str | None = None) -> bool:
    """Puerta de actualización obligatoria. True = bloquear y salir.

    Compara la versión publicada en la Store (DisplayCatalog) con la
    instalada. Solo bloquea si la de la Store es estrictamente mayor
    (fail-open en todo lo demás). Al bloquear ya ha impreso el aviso y
    abierto la ventana de actualizaciones; el llamador debe terminar.
    """
    if not store_product_id:
        return False
    instalada = version_de_full_name(package_full_name() or "")
    if instalada is None:
        return False
    tienda = version_tienda(store_product_id)
    if tienda is None or tienda <= instalada:
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
