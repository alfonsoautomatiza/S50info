import builtins
import json
import logging
import os
import runpy
import shutil
import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import typer
import click
from pysage50e import apiSAGE50
from pysage50e.sage_debug_config import configure_debug_logging
from rich import print as rprint
from rich.markup import escape
from rich.panel import Panel

import s50setup
import s50onboarding
from s50version import __version__ as S50INFO_VERSION
from s50version import STORE_PRODUCT_ID

# Carga resiliente de librerías compartidas en mislibrerias (WSL y Windows)
def _add_mislibrerias_to_path():
    for _libs in (
        Path("/home/alfonso/py/mislibrerias"),
        Path("P:/mislibrerias"),
    ):
        if _libs.is_dir():
            sys.path.insert(0, str(_libs))
            break


# Carga resiliente de wertyfeedback (sistema compartido de informes de error)
try:
    import wertyfeedback
except ImportError:
    _add_mislibrerias_to_path()
    try:
        import wertyfeedback
    except ImportError:
        wertyfeedback = None

# Carga resiliente de libupdatemsix (librería compartida en mislibrerias)
try:
    import libupdatemsix
except ImportError:
    _add_mislibrerias_to_path()
    try:
        import libupdatemsix
    except ImportError:
        libupdatemsix = None
        logging.warning("libupdatemsix no disponible: puerta de actualizacion desactivada")

try:
    import s50proceso
except Exception as e:
    logging.warning(f"No se pudo cargar s50proceso (hardware/sistema): {e}")

    # Crear un módulo dummy para que el programa continúe
    class _DummyProceso:
        class proceso:
            def __init__(self, *args, **kwargs):
                pass

    s50proceso = _DummyProceso()

# Activar DEBUG detallado si .env tiene DEBUG=True/Si/1
_debug_active = configure_debug_logging()

MANUAL_URL = os.getenv("MANUAL_URL", "https://alfonsoautomatiza.github.io/Sage50bi/")
SAGE50BI_URL = os.getenv("SAGE50BI_URL", "https://www.alfonsoautomatiza.com/s50-bi")
USAGE_PROMPT_FIRST_USE = 5
USAGE_PROMPT_INTERVAL = 20
USAGE_PROMPT_FILE = "usage_prompt.json"
CONFIG_FILE = "config.ini"
USAGE_PROMPT_UTM = {
    "utm_source": "cli",
    "utm_medium": "post_command",
    "utm_campaign": "s50info_contact",
}

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "S50Info - herramienta CLI para consultar, exportar y mantener SAGE50. "
        "Usa los subcomandos `info`, `sql`, `export`, `run`, `reset`, `feedback`, `manual` y `version`."
    ),
)

_cwd_original = Path.cwd()
_feedback = None


def _app_state_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "s50info"
    return Path.home() / ".s50info"


def _get_feedback():
    """Crea el colector de feedback configurado para s50info."""
    if wertyfeedback is None:
        return None
    return wertyfeedback.get_feedback(
        app_name="s50info",
        state_dir=_app_state_dir(),
        support_email=os.getenv("S50INFO_SUPPORT_EMAIL", ""),
    )


def _send_feedback_error(exc: BaseException) -> None:
    """Registra un error y, en modo interactivo, pregunta si enviar el log."""
    if wertyfeedback is None:
        return
    wertyfeedback.send_on_error(_feedback, exc)


def _ensure_config_path() -> Path:
    config_path = _app_state_dir() / CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.touch(exist_ok=True)
    return config_path


def _directorio_ejecutable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _sincronizar_carpeta_scripts() -> None:
    """Regenera la carpeta `script` en el directorio de trabajo si no existe."""
    origen = _directorio_ejecutable() / "script"
    destino = Path("script")
    if not destino.is_dir() and origen.is_dir():
        try:
            shutil.copytree(origen, destino)
        except OSError as exc:
            logging.warning(f"No se pudo regenerar la carpeta `script`: {exc}")


def _inicializar_directorio_trabajo() -> None:
    """Fija el directorio de trabajo en el estado de la app (APPDATA) y regenera `script`."""
    global _cwd_original
    try:
        state_dir = _app_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        _cwd_original = Path.cwd()
        os.chdir(state_dir)
        _sincronizar_carpeta_scripts()
    except OSError as exc:
        logging.warning(f"No se pudo usar {_app_state_dir()} como Directorio Config.ini: {exc}")


def _sage_terminal_not_found(api_obj) -> bool:
    try:
        terminal_path = api_obj.confsage50.cvariables.get("api#terminal", "")
        return not terminal_path or not (Path(terminal_path) / CONFIG_FILE).is_file()
    except (AttributeError, TypeError, ValueError, OSError):
        return False


def _ejecutar_asistente_terminal(config_path) -> bool:
    """Lanza el asistente de configuración inicial. True si quedó terminal válido."""
    terminal = s50setup.asistente_terminal(config_path)
    if terminal is None:
        rprint()
        rprint("[yellow]Sin un SAGE 50 instalado, s50info no puede consultar datos.[/yellow]")
        rprint("[grey70]Vuelve a ejecutar s50info cuando SAGE 50 esté instalado.[/grey70]")
        return False
    return True


def _crear_proceso():
    try:
        rprint(f"[grey70]Directorio Config.ini: {escape(str(_app_state_dir()))}[/grey70]")
        rprint("[grey70]Conectando a SAGE50...[/grey70]")
        config_path = _ensure_config_path()
        for intento in range(2):
            if s50setup.necesita_asistente(config_path) and not _ejecutar_asistente_terminal(
                config_path
            ):
                return None
            api_obj = apiSAGE50(dirconfig=str(config_path.parent))
            proceso_obj = s50proceso.proceso(
                api=api_obj,
                config_path=config_path,
                directorio_resultados=str(_cwd_original / "resultados"),
            )
            if getattr(api_obj, "lconecto", False):
                rprint("[green]✓ Conectado a SAGE50[/green]")
                return proceso_obj
            terminal_malo = _sage_terminal_not_found(api_obj)
            if terminal_malo:
                rprint("[yellow]El terminal SAGE50 configurado no es válido.[/yellow]")
            if intento == 0 and terminal_malo:
                continue
            if terminal_malo:
                rprint("[bold red]Error:[/bold red] Terminal de Sage 50 no encontrado.")
            else:
                rprint("[bold red]Error:[/bold red] No se pudo conectar con SAGE50")
            return None
        return None
    except Exception as exc:
        rprint(f"[bold red]Error al conectar con SAGE50:[/bold red] {escape(str(exc))}")
        logging.error(f"Error conectando SAGE50: {exc}")
        return None


def _contact_url_with_utm(url: str = SAGE50BI_URL) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(USAGE_PROMPT_UTM)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _usage_prompt_state_path() -> Path:
    return _app_state_dir() / USAGE_PROMPT_FILE


def _should_show_usage_prompt(successful_uses: int, last_prompt_successful_uses: int) -> bool:
    if successful_uses < USAGE_PROMPT_FIRST_USE:
        return False
    if successful_uses == last_prompt_successful_uses:
        return False
    return (successful_uses - USAGE_PROMPT_FIRST_USE) % USAGE_PROMPT_INTERVAL == 0


def _record_successful_use_and_maybe_show_cta(state_path: Path | None = None) -> None:
    state_path = state_path or _usage_prompt_state_path()

    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        if not isinstance(state, dict):
            state = {}
    except (OSError, json.JSONDecodeError):
        state = {}

    try:
        successful_uses = int(state.get("successful_uses", 0) or 0) + 1
        last_prompt_successful_uses = int(state.get("last_prompt_successful_uses", 0) or 0)
    except (TypeError, ValueError):
        successful_uses = 1
        last_prompt_successful_uses = 0
    show_prompt = _should_show_usage_prompt(successful_uses, last_prompt_successful_uses)

    state["successful_uses"] = successful_uses
    if show_prompt:
        state["last_prompt_successful_uses"] = successful_uses

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        return

    if show_prompt:
        rprint(
            "[bold #ffb000]¿Querés que te ayudemos a llevar esto más lejos? "
            f"Contactanos cuando quieras: {_contact_url_with_utm()}[/bold #ffb000]"
        )


def _pausa_final():
    rprint("\n[bold green]Presione UNA tecla para continuar...[/bold green]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        # stdin no interactivo (tareas programadas, pipes) o Ctrl+C: continuar.
        pass


def _inyectar_helpers_script(proceso_obj):
    from s50script import (
        exportar_samples,
        query_to_dict,
        samplebi,
        samples_disponibles,
        seleccionar_samples,
    )

    builtins.s50info_proceso = proceso_obj
    builtins.samplebi = samplebi
    builtins.query_to_dict = query_to_dict
    builtins.samples_disponibles = samples_disponibles
    builtins.seleccionar_samples = seleccionar_samples
    builtins.exportar_samples = exportar_samples

    proceso_obj.samplebi = lambda nombre, **kwargs: samplebi(nombre, proc=proceso_obj, **kwargs)
    proceso_obj.query_to_dict = lambda sql, **kwargs: query_to_dict(sql, proc=proceso_obj, **kwargs)
    proceso_obj.samples_disponibles = samples_disponibles
    proceso_obj.seleccionar_samples = seleccionar_samples
    proceso_obj.exportar_samples = lambda nombres, **kwargs: exportar_samples(
        nombres, proc=proceso_obj, **kwargs
    )

    return {
        "samplebi": builtins.samplebi,
        "query_to_dict": builtins.query_to_dict,
        "samples_disponibles": builtins.samples_disponibles,
        "seleccionar_samples": builtins.seleccionar_samples,
        "exportar_samples": builtins.exportar_samples,
    }


def _normalizar_sqlyear_desde_shell(ctx: typer.Context, sqlyear: str) -> str:
    if sqlyear == "@":
        return "*"

    if not ctx.args:
        return sqlyear

    candidatos = [sqlyear, *ctx.args]
    if all(Path(valor).exists() for valor in candidatos):
        rprint(
            "[yellow]Aviso:[/yellow] El shell expandio `*` a archivos locales. "
            "Se interpretara `--sqlyear` como `*`. Para evitarlo, usa `--sqlyear @`."
        )
        ctx.args.clear()
        return "*"

    return sqlyear


def _abrir_manual() -> None:
    """Abre el manual que proporciona la licencia en el navegador."""
    s50setup._abrir_url(MANUAL_URL)


def _recordar_ayuda() -> None:
    rprint("[grey70]Usa -h o --help para ver la lista de comandos.[/grey70]")


def _recordar_sage50bi() -> None:
    """Llamada a Sage50BI: sutil, clara de que es otro producto, y vistosa."""
    rprint(
        Panel(
            "¿Necesitas [bold]informes y cuadros de mando visuales[/bold] de tu SAGE50,\n"
            "sin comandos ni programación?\n\n"
            "También hacemos [bold cyan]Sage50BI[/bold cyan]: otro producto, pensado\n"
            "para perfiles no técnicos.\n"
            f"[link={SAGE50BI_URL}]→ Descubre Sage50BI[/link]",
            title="[bold cyan]Sage50BI · informes visuales[/bold cyan]",
            border_style="cyan",
        )
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    grupo_comunes: str | None = typer.Option(
        None,
        "--grupo-comunes",
        "-c",
        help="Grupo de comunes a usar. Si no se indica, se toma el de config.ini.",
    ),
    manual: bool = typer.Option(
        False,
        "--manual",
        "-m",
        "--m",
        help="Abre el manual que proporciona la licencia en el navegador.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        "--v",
        help="Muestra la versión del programa.",
    ),
):
    if version:
        rprint(f"s50info v{S50INFO_VERSION}")
        _recordar_ayuda()
        raise typer.Exit()
    if manual:
        _abrir_manual()
        rprint(f"[grey70]Manual: {MANUAL_URL}[/grey70]")
        _recordar_ayuda()
        raise typer.Exit()

    # Puerta de actualización obligatoria (solo instalaciones MSIX/Store).
    if libupdatemsix is not None and libupdatemsix.puerta_update_obligatorio(
        nombre_app="s50info", store_product_id=STORE_PRODUCT_ID
    ):
        raise typer.Exit(1)

    _inicializar_directorio_trabajo()
    global _feedback
    _feedback = _get_feedback()
    s50onboarding.mostrar_if_necesario(_app_state_dir())
    if ctx.invoked_subcommand is None:
        rprint(f"[grey70]Directorio de trabajo: {Path.cwd()}[/grey70]")
    if ctx.invoked_subcommand is not None:
        return

    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()

    try:
        proceso_obj.info(pausa=True, grupo_comunes=grupo_comunes)
        _record_successful_use_and_maybe_show_cta()
        _recordar_sage50bi()
        _recordar_ayuda()
        _pausa_final()
    except Exception as exc:
        logging.error(exc)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {escape(str(exc))}")
        _send_feedback_error(exc)
        raise typer.Exit(1)


@app.command("manual")
def manual_cmd() -> None:
    """Abre el manual que proporciona la licencia en el navegador."""
    _abrir_manual()
    rprint(f"[grey70]Manual: {MANUAL_URL}[/grey70]")
    _recordar_ayuda()


@app.command("version")
def version_cmd() -> None:
    """Muestra la versión del programa."""
    rprint(f"s50info v{S50INFO_VERSION}")
    _recordar_ayuda()


@app.command("info")
def info_cmd(
    grupo_comunes: str | None = typer.Option(
        None,
        "--grupo-comunes",
        "-c",
        help="Grupo de comunes a usar. Si no se indica, se toma el de config.ini.",
    ),
):
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()
    try:
        proceso_obj.info(pausa=True, grupo_comunes=grupo_comunes)
        _record_successful_use_and_maybe_show_cta()
        _recordar_sage50bi()
        _recordar_ayuda()
        _pausa_final()
    except Exception as exc:
        logging.error(exc)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {escape(str(exc))}")
        _send_feedback_error(exc)
        raise typer.Exit(1)


@app.command("sql", context_settings={"allow_extra_args": True, "ignore_unknown_options": False})
def sql_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ...,
        help=(
            "Consulta SQL de lectura a ejecutar. Soporta sintaxis SAGE50 como "
            "`#clientes`, `GESTION!CLIENTES`, `[COMU]tabla` y `COMUNES!tabla`."
        ),
    ),
    sqlyear: str = typer.Option(
        "+",
        "--sqlyear",
        "-a",
        help=(
            "Years a usar para resolver tablas de gestion. `+` usa el ultimo year, "
            "`*` o `@` usan todos, tambien acepta un year concreto o una lista separada por comas."
        ),
    ),
    grupo_comunes: str | None = typer.Option(
        None,
        "--grupo-comunes",
        "-c",
        help=(
            "Grupo de comunes a usar para resolver years y tablas COMUNES. "
            "Si no se indica, se toma el de `config.ini`. Admite `4` o `COMU0004`."
        ),
    ),
    groupby: str | None = typer.Option(
        None,
        "--groupby",
        "-b",
        help=(
            "Agrupa el resultado final tras unir varios years. "
            "Ejemplo: `--groupby CODIGO` con `-a @`."
        ),
    ),
    sage50: bool = typer.Option(
        False,
        "--sage50",
        "-s",
        help=(
            "Muestra tambien la consulta equivalente en sintaxis SAGE50, "
            "sustituyendo `#tabla` por `GESTION!tabla` y `[COMU]tabla` por `COMUNES!tabla`."
        ),
    ),
):
    """
    Ejecuta una consulta SQL de solo lectura sobre SAGE50.

    El comando resuelve la sintaxis SAGE50 a SQL Server real segun el grupo de
    comunes y los years seleccionados. Antes de ejecutar muestra por consola el
    grupo usado y los years resueltos.

    Reglas principales:
    - Solo permite consultas `SELECT` o `WITH`
    - `#tabla` se resuelve contra tablas de gestion segun `--sqlyear`
    - `[COMU]tabla` o `COMUNES!tabla` usan el grupo de comunes activo
    - `--grupo-comunes` sobreescribe el comunes de `config.ini`
    - `--groupby` agrupa el resultado final tras unir varios years
    - `--sage50` muestra la consulta en formato SAGE50 para copiarla o revisarla

    Ejemplos:
    - `s50info sql "select * from #clientes"`
    - `s50info sql "select * from #clientes" --sqlyear @`
    - `s50info sql "select CODIGO, MAX(NOMBRE) from #clientes" -a @ -b CODIGO`
    - `s50info sql "select * from [COMU]gruposemp" --grupo-comunes 4`
    - `s50info sql "select * from #clientes" --sage50`
    """
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()
    sqlyear = _normalizar_sqlyear_desde_shell(ctx, sqlyear)
    success = proceso_obj.sql(
        query,
        sqlyear=sqlyear,
        grupo_comunes=grupo_comunes,
        groupby=groupby,
        sage50=sage50,
    )
    if success is True:
        _record_successful_use_and_maybe_show_cta()


@app.command("export", context_settings={"allow_extra_args": True, "ignore_unknown_options": False})
def export_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ...,
        help=(
            "Consulta SQL de lectura a exportar. Soporta sintaxis SAGE50 como "
            "`#clientes`, `GESTION!CLIENTES`, `[COMU]tabla` y `COMUNES!tabla`."
        ),
    ),
    sqlyear: str = typer.Option(
        "+",
        "--sqlyear",
        "-a",
        help="Año o lista de años SQL a usar (ej: +, *, @, 2025, 2024,2025). El sufijo de letras se resuelve según el grupo de comunes.",
    ),
    grupo_comunes: str | None = typer.Option(
        None,
        "--grupo-comunes",
        "-c",
        help="Grupo de comunes a usar. Si no se indica, se toma el de config.ini.",
    ),
    groupby: str | None = typer.Option(
        None,
        "--groupby",
        "-b",
        help="Agrupa el resultado final tras unir varios years.",
    ),
    sage50: bool = typer.Option(
        False,
        "--sage50",
        "-s",
        help="Muestra tambien la consulta equivalente en sintaxis SAGE50 antes de exportar.",
    ),
    formato: str = typer.Option("txt", "--formato", "-f", help="Formato de exportación"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Nombre base del archivo de salida (sin extensión)"
    ),
    plantilla: str | None = typer.Option(
        None, "--plantilla", "-t", help="Ruta a plantilla personalizada para formato TXT"
    ),
    comprimir: bool = typer.Option(False, "--zip", "-z", help="Comprimir resultado en ZIP"),
):
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()
    sqlyear = _normalizar_sqlyear_desde_shell(ctx, sqlyear)
    if plantilla and not Path(plantilla).is_absolute():
        # Ruta relativa del usuario: anclarla al cwd original, no a APPDATA.
        plantilla = str(_cwd_original / plantilla)
    rprint(f"[bold cyan]Ejecutando SQL export a {formato}...[/bold cyan]")
    try:
        success = proceso_obj.sql2doc(
            query,
            sqlyear=sqlyear,
            grupo_comunes=grupo_comunes,
            groupby=groupby,
            sage50=sage50,
            formato=formato,
            nombre_archivo=output,
            plantilla=plantilla,
            comprimir=comprimir,
        )
    except Exception as exc:
        logging.error(exc)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {escape(str(exc))}")
        _send_feedback_error(exc)
        raise typer.Exit(1)
    if success is True:
        _record_successful_use_and_maybe_show_cta()


@app.command("run")
def run_cmd(
    ruta: str | None = typer.Argument(
        None,
        help="Archivo .py o directorio con scripts. Si no se indica, usa `script` si existe.",
    ),
    skip_polars_cpu_check: bool = typer.Option(
        False,
        "--skip-polars-cpu-check",
        "--polars-skip-cpu-check",
        help=(
            "Activa POLARS_SKIP_CPU_CHECK=1 antes de ejecutar scripts externos que usan Polars. "
            "Usalo solo si el script necesita Polars en hardware antiguo."
        ),
    ),
):
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()

    if ruta is None or not ruta.strip():
        ruta = "script"
        rprint("[grey70]No se indicó ruta. Se intentará usar `script` automáticamente.[/grey70]")
        path = Path(ruta)
    else:
        # Ruta relativa del usuario: anclarla al cwd original, no a APPDATA.
        path = Path(ruta.strip())
        if not path.is_absolute():
            path = _cwd_original / path

    if not path.exists():
        rprint(f"[bold red]Error:[/bold red] No se encontró: '{escape(ruta)}'")
        rprint("[grey70]Recomendación:[/grey70] usa la carpeta `script` para automatizar este comando.")
        rprint(f"[grey70]Buscando en:[/grey70] {escape(str(path.resolve()))}")
        raise typer.Exit(1)

    if skip_polars_cpu_check:
        os.environ["POLARS_SKIP_CPU_CHECK"] = "1"

    if path.is_dir():
        rprint(
            Panel(
                f"[bold blue]Ejecutando scripts de carpeta:[/bold blue] {ruta}",
                title="Info",
                border_style="blue",
            )
        )
        py_files = sorted(path.glob("*.py"))
        if not py_files:
            rprint(f"[yellow]Aviso:[/yellow] No se encontraron archivos .py en '{ruta}'")
            raise typer.Exit()

        failed = False
        for script_file in py_files:
            rprint(f"[cyan]Ejecutando:[/cyan] {script_file.name}")
            try:
                helpers = _inyectar_helpers_script(proceso_obj)
                script_globals = {
                    "__name__": "__main__",
                    "__file__": str(script_file),
                    "proceso": proceso_obj,
                    **helpers,
                }
                runpy.run_path(str(script_file), init_globals=script_globals, run_name="__main__")
            except Exception as exc:
                failed = True
                rprint(f"[bold red]Error al ejecutar {script_file.name}:[/bold red] {exc}")
                print(traceback.format_exc())
                logging.error(f"Error ejecutando script externo: {exc}")
                _send_feedback_error(exc)
        if failed:
            raise typer.Exit(1)
        _record_successful_use_and_maybe_show_cta()
        _pausa_final()
        return

    if path.suffix != ".py":
        rprint(f"[bold red]Error:[/bold red] El archivo '{ruta}' no es un archivo Python (.py)")
        raise typer.Exit(1)

    rprint(
        Panel(
            f"[bold blue]Ejecutando script externo:[/bold blue] {ruta}",
            title="Info",
            border_style="blue",
        )
    )
    try:
        helpers = _inyectar_helpers_script(proceso_obj)
        script_globals = {
            "__name__": "__main__",
            "__file__": str(path),
            "proceso": proceso_obj,
            **helpers,
        }
        runpy.run_path(str(path), init_globals=script_globals, run_name="__main__")
        _record_successful_use_and_maybe_show_cta()
        _pausa_final()
    except Exception as exc:
        rprint(f"[bold red]Error al ejecutar el script {ruta}:[/bold red] {exc}")
        logging.error(f"Error ejecutando script externo: {exc}")
        print(exc)
        print(traceback.format_exc())
        _send_feedback_error(exc)
        raise typer.Exit(1)


@app.command("reset")
def reset_cmd():
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()
    proceso_obj.reset_log()


@app.command("feedback")
def feedback_cmd(
    mensaje: str | None = typer.Argument(
        None,
        help="Mensaje opcional para incluir en el informe.",
    ),
):
    """Envía el log de la aplicación a soporte (requiere S50INFO_SUPPORT_EMAIL)."""
    _inicializar_directorio_trabajo()
    feedback = _get_feedback()
    if feedback is None:
        rprint(
            "[yellow]Aviso:[/yellow] El sistema de feedback no está disponible. "
            "Comprueba que las librerías Werty están accesibles."
        )
        raise typer.Exit()

    if not feedback.support_email:
        rprint(
            "[yellow]Aviso:[/yellow] No está configurado el email de soporte. "
            "Define la variable de entorno S50INFO_SUPPORT_EMAIL."
        )
        raise typer.Exit()

    enviado = feedback.ask_and_send_log(
        context=None,
        body=mensaje,
        ask_permission_callback=lambda: wertyfeedback.console_ask_permission(
            "¿Quieres enviar el log a soporte"
        ),
    )
    if enviado:
        rprint("[green]Log enviado a soporte.[/green]")
    else:
        rprint("[grey70]No se envió el log.[/grey70]")


def _cli_main() -> None:
    """Punto de entrada: ante un error de uso muestra el recordatorio de ayuda."""
    try:
        app(standalone_mode=False)
    except click.exceptions.UsageError as exc:
        exc.show()
        _recordar_ayuda()
        raise SystemExit(exc.exit_code)
    except click.exceptions.Exit as exc:
        raise SystemExit(exc.exit_code)
    except click.exceptions.Abort:
        rprint("[red]Cancelado.[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    _cli_main()
