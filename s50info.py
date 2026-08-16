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
from pysage50e import apiSAGE50
from pysage50e.sage_debug_config import configure_debug_logging
from rich import print as rprint
from rich.panel import Panel

import s50setup

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

SAGE50BI_URL = os.getenv("SAGE50BI_URL", "https://sage50eia.com/s50info")
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
        "Usa los subcomandos `info`, `sql`, `export`, `run` y `reset`."
    ),
)

_cwd_original = Path.cwd()


def _app_state_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "s50info"
    return Path.home() / ".s50info"


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
        rprint("[dim]Vuelve a ejecutar s50info cuando SAGE 50 esté instalado.[/dim]")
        return False
    return True


def _crear_proceso():
    try:
        rprint(f"[dim]Directorio Config.ini: {_app_state_dir()}[/dim]")
        rprint("[dim]Conectando a SAGE50...[/dim]")
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
        rprint(f"[bold red]Error al conectar con SAGE50:[/bold red] {exc}")
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
    input()


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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    grupo_comunes: str | None = typer.Option(
        None,
        "--grupo-comunes",
        "-c",
        help="Grupo de comunes a usar. Si no se indica, se toma el de config.ini.",
    ),
):
    _inicializar_directorio_trabajo()
    if ctx.invoked_subcommand is not None:
        return

    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()

    try:
        proceso_obj.info(pausa=True, grupo_comunes=grupo_comunes)
        _record_successful_use_and_maybe_show_cta()
        _pausa_final()
    except Exception as exc:
        logging.error(exc)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {exc}")
        raise typer.Exit(1)


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
    proceso_obj.info(pausa=True, grupo_comunes=grupo_comunes)
    _record_successful_use_and_maybe_show_cta()
    _pausa_final()


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
        help="Año o lista de años SQL a usar (ej: +, *, @, 2025JX, 2024JX,2025JX)",
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
    rprint(f"[bold cyan]Ejecutando SQL export a {formato}...[/bold cyan]")
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
        rprint("[dim]No se indicó ruta. Se intentará usar `script` automáticamente.[/dim]")

    path = Path(ruta.strip())
    if not path.exists():
        rprint(f"[bold red]Error:[/bold red] No se encontró: '{ruta}'")
        rprint("[dim]Recomendación:[/dim] usa la carpeta `script` para automatizar este comando.")
        rprint(f"[dim]Buscando en:[/dim] {path.resolve()}")
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
            "__file__": ruta,
            "proceso": proceso_obj,
            **helpers,
        }
        runpy.run_path(ruta, init_globals=script_globals, run_name="__main__")
        _record_successful_use_and_maybe_show_cta()
        _pausa_final()
    except Exception as exc:
        rprint(f"[bold red]Error al ejecutar el script {ruta}:[/bold red] {exc}")
        logging.error(f"Error ejecutando script externo: {exc}")
        print(exc)
        print(traceback.format_exc())
        raise typer.Exit(1)


@app.command("reset")
def reset_cmd():
    proceso_obj = _crear_proceso()
    if proceso_obj is None:
        raise typer.Exit()
    proceso_obj.reset_log()


if __name__ == "__main__":
    app()
