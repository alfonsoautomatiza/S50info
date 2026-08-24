"""Asistente de configuración inicial de SAGE50 para s50info.

Cuando s50info arranca y no hay un terminal SAGE50 configurado (típico del
primer arranque o de un equipo sin SAGE50 instalado), este módulo ofrece un
asistente que:

- detecta instalaciones de SAGE50 (registro de Windows y rutas típicas),
- permite indicar manualmente la carpeta del terminal,
- abre la descarga oficial de SAGE50 si el usuario quiere instalarlo,
- guarda el terminal elegido en `config.ini` (sección [API], clave terminal).

La carpeta "terminal" de SAGE50 es la que contiene su propio config.ini
(p.ej. `C:\\Sage50\\Sage50Term`), igual que valida `_sage_terminal_not_found`.
"""

import configparser
import logging
import os
import sys
import webbrowser
from pathlib import Path

from rich import print as rprint
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt

_logger = logging.getLogger(__name__)

SAGE50_DOWNLOAD_URL = os.getenv(
    "SAGE50_DOWNLOAD_URL", "http://descargas.sage.es/sage50/sage50.zip"
)
CONFIG_FILE = "config.ini"
_RUTA_UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
_MAX_CARPETAS_EXPLORADAS = 500
_MAX_TERMINALES = 20


def es_terminal_valido(ruta) -> bool:
    """True si `ruta` es un directorio que contiene config.ini."""
    try:
        ruta = Path(ruta)
        return ruta.is_dir() and (ruta / CONFIG_FILE).is_file()
    except (TypeError, ValueError, OSError):
        return False


def _leer_config(config_path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    try:
        if config_path and Path(config_path).exists():
            parser.read(config_path, encoding="utf-8")
    except (OSError, configparser.Error) as exc:
        _logger.warning("config.ini ilegible (%s): %s", config_path, exc)
    return parser


def terminal_configurado(config_path) -> str:
    """Devuelve el valor de [API] terminal (cadena vacía si no está)."""
    parser = _leer_config(config_path)
    try:
        return parser.get("API", "terminal", fallback="").strip()
    except (configparser.Error, ValueError):
        return ""


def necesita_asistente(config_path) -> bool:
    """True si falta el terminal o apunta a una carpeta no válida."""
    terminal = terminal_configurado(config_path)
    return not terminal or not es_terminal_valido(terminal)


def guardar_terminal(config_path, terminal) -> None:
    """Escribe [API] terminal preservando el resto de secciones y claves."""
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    parser = _leer_config(config_path)
    if not parser.has_section("API"):
        parser.add_section("API")
    parser.set("API", "terminal", str(terminal))
    with open(config_path, "w", encoding="utf-8") as handle:
        parser.write(handle)


def buscar_terminales_en(base, profundidad: int = 2) -> list[Path]:
    """Busca carpetas terminal (con config.ini) bajo `base`, hasta `profundidad`."""
    try:
        base = Path(base)
    except (TypeError, ValueError):
        return []
    if not base.is_dir():
        return []

    encontrados = []
    if es_terminal_valido(base):
        encontrados.append(base)

    nivel = [base]
    exploradas = 0
    for _ in range(max(profundidad, 0)):
        siguiente = []
        for carpeta in nivel:
            if exploradas >= _MAX_CARPETAS_EXPLORADAS:
                break
            exploradas += 1
            try:
                hijos = sorted(carpeta.iterdir())
            except OSError:
                continue
            for hijo in hijos:
                if len(encontrados) >= _MAX_TERMINALES:
                    break
                if not hijo.is_dir() or hijo.name.startswith("."):
                    continue
                if es_terminal_valido(hijo):
                    encontrados.append(hijo)
                siguiente.append(hijo)
        nivel = siguiente

    return list(dict.fromkeys(encontrados))


def rutas_tipicas() -> list[Path]:
    """Rutas donde SAGE50 suele instalarse."""
    candidatas = [
        Path("C:/Sage50"),
        Path("C:/Sage"),
        Path("D:/Sage50"),
    ]
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        valor = os.getenv(variable)
        if valor:
            candidatas.append(Path(valor) / "Sage50")
            candidatas.append(Path(valor) / "Sage")

    unicas = []
    for ruta in candidatas:
        if ruta not in unicas:
            unicas.append(ruta)
    return unicas


def buscar_en_registro() -> list[Path]:
    """Busca instalaciones de SAGE50 en las claves de desinstalación de Windows."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []

    vistas = (
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    )
    resultados = []
    for hive, vista in vistas:
        try:
            clave = winreg.OpenKey(hive, _RUTA_UNINSTALL, 0, winreg.KEY_READ | vista)
        except OSError:
            continue
        with clave:
            indice = 0
            while True:
                try:
                    subnombre = winreg.EnumKey(clave, indice)
                except OSError:
                    break
                indice += 1
                try:
                    with winreg.OpenKey(
                        clave, subnombre, 0, winreg.KEY_READ | vista
                    ) as subclave:
                        nombre = str(winreg.QueryValueEx(subclave, "DisplayName")[0]).lower()
                        if "sage" not in nombre or "50" not in nombre:
                            continue
                        try:
                            ubicacion = str(
                                winreg.QueryValueEx(subclave, "InstallLocation")[0]
                            ).strip()
                        except OSError:
                            ubicacion = ""
                except OSError:
                    continue
                if ubicacion:
                    resultados.append(Path(ubicacion))
    return resultados


def detectar_terminales() -> list[Path]:
    """Combina registro y rutas típicas; devuelve carpetas terminal válidas."""
    bases = [*buscar_en_registro(), *rutas_tipicas()]
    encontrados = []
    for base in bases:
        for terminal in buscar_terminales_en(base):
            if terminal not in encontrados:
                encontrados.append(terminal)

    def clave_orden(terminal: Path):
        return (0 if "term" in terminal.name.lower() else 1, str(terminal).lower())

    return sorted(encontrados, key=clave_orden)


def construir_menu(candidatos: list[Path]) -> tuple[list[tuple[str, Path | None]], str]:
    """Devuelve (opciones, texto) del menú de configuración inicial."""
    lineas = [
        "[bold]S50Info necesita SAGE 50 instalado en este equipo[/bold]",
        "para poder consultar sus datos, y no hay un terminal válido configurado.",
        "",
    ]
    if candidatos:
        lineas.append("Se han encontrado estas instalaciones de SAGE 50:")

    opciones: list[tuple[str, Path | None]] = []
    numero = 1
    for terminal in candidatos:
        opciones.append(("usar", terminal))
        lineas.append(f"  [{numero}] Usar SAGE 50 detectado en: [cyan]{escape(str(terminal))}[/cyan]")
        numero += 1

    opciones.append(("manual", None))
    lineas.append(f"  [{numero}] Indicar la carpeta del terminal SAGE 50")
    numero += 1
    opciones.append(("descargar", None))
    lineas.append(
        f"  [{numero}] Descargar SAGE 50 ahora (se abrirá: {SAGE50_DOWNLOAD_URL})"
    )
    numero += 1
    opciones.append(("salir", None))
    lineas.append(f"  [{numero}] Salir")
    return opciones, "\n".join(lineas)


def _resolver_terminal_manual(ruta_raw) -> Path | None:
    """Acepta la carpeta terminal, su config.ini, o una carpeta que la contenga."""
    valor = str(ruta_raw or "").strip().strip('"').strip("'")
    if not valor:
        return None
    try:
        ruta = Path(valor).expanduser()
    except (TypeError, ValueError, OSError):
        return None
    if es_terminal_valido(ruta):
        return ruta
    if ruta.is_file() and ruta.name.lower() == CONFIG_FILE:
        return ruta.parent if es_terminal_valido(ruta.parent) else None
    if ruta.is_dir():
        hallados = buscar_terminales_en(ruta, profundidad=1)
        if hallados:
            return hallados[0]
    return None


def _abrir_url(url: str) -> None:
    """Abre la URL con el navegador por defecto (robusto en builds frozen)."""
    startfile = getattr(os, "startfile", None)
    if sys.platform == "win32" and startfile is not None:
        try:
            startfile(url)
            return
        except OSError:
            _logger.warning("os.startfile falló para %s; pruebo webbrowser", url)
    try:
        webbrowser.open(url)
    except (OSError, webbrowser.Error):
        _logger.warning("No se pudo abrir %s", url)


def asistente_terminal(
    config_path,
    *,
    detectar=None,
    abrir_url=None,
    elegir=None,
    pedir_ruta=None,
    mostrar=None,
) -> Path | None:
    """Asistente interactivo de configuración del terminal SAGE50.

    Devuelve la carpeta terminal elegida (ya guardada en config.ini) o None
    si el usuario sale/cancela o la entrada no es interactiva.
    """
    config_path = Path(config_path)
    detectar = detectar or detectar_terminales
    abrir_url = abrir_url or _abrir_url
    mostrar = mostrar or rprint

    if elegir is None:

        def elegir(mensaje, choices):
            return Prompt.ask(mensaje, choices=choices)

    if pedir_ruta is None:

        def pedir_ruta(mensaje):
            return Prompt.ask(mensaje)

    while True:
        candidatos = list(detectar() or [])
        opciones, texto = construir_menu(candidatos)
        try:
            mostrar(Panel(texto, title="Configuración inicial", border_style="cyan"))
            eleccion = elegir(
                "¿Qué quieres hacer?",
                choices=[str(i) for i in range(1, len(opciones) + 1)],
            )
        except (EOFError, KeyboardInterrupt):
            return None

        accion, dato = opciones[int(eleccion) - 1]

        if accion == "usar" and dato is not None:
            guardar_terminal(config_path, dato)
            mostrar(f"[green]✓ Terminal de SAGE 50 guardado: {dato}[/green]")
            return dato

        if accion == "manual":
            mostrar(
                "[grey70]El terminal es la carpeta de SAGE 50 que contiene config.ini "
                "(p.ej. C:\\Sage50\\Sage50Term).[/grey70]"
            )
            try:
                ruta_raw = pedir_ruta("Carpeta del terminal SAGE 50")
            except (EOFError, KeyboardInterrupt):
                return None
            terminal = _resolver_terminal_manual(ruta_raw)
            if terminal is not None:
                guardar_terminal(config_path, terminal)
                mostrar(f"[green]✓ Terminal de SAGE 50 guardado: {terminal}[/green]")
                return terminal
            mostrar(
                "[yellow]Esa carpeta no contiene un terminal SAGE 50 válido "
                "(falta config.ini).[/yellow]"
            )
            continue

        if accion == "descargar":
            mostrar(f"[cyan]Abriendo la descarga de SAGE 50: {SAGE50_DOWNLOAD_URL}[/cyan]")
            mostrar(
                "[grey70]Instala SAGE 50 y vuelve al menú para detectarlo "
                "automáticamente.[/grey70]"
            )
            try:
                abrir_url(SAGE50_DOWNLOAD_URL)
            except (OSError, webbrowser.Error):
                _logger.warning("No se pudo abrir la descarga de SAGE 50")
            continue

        return None
