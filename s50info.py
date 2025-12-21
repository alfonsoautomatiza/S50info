import logging
import sys
import runpy
import typer
from types import SimpleNamespace
from typing import Optional
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

# Local imports
import libwertyupdate
import proceso

app = typer.Typer(add_completion=False, help="Herramienta para ejecutar SQL y procesos Sage50")
console = Console()

def get_params(**kwargs):
    """Crea un objeto compatible con argparse.Namespace para pasar a proceso"""
    return SimpleNamespace(**kwargs)

@app.command()
def main(
    noupdate: Optional[str] = typer.Option(None, "--noupdate", "-no", help="No actualiza y el motivo"),
    reset: bool = typer.Option(False, "--reset", "-r", help="Destino de los XML generados por defecto carpeta .\\resultados"),
    sql: Optional[str] = typer.Option(None, "--sql", "-s", help="Ejecucion codigo sql"),
    clave: Optional[str] = typer.Option(None, "--clave", "-c", help="Obtiene la clave Sage50 sql desde LICENCIA SAGE50"),
    sqltodic: Optional[str] = typer.Option(None, "--sqltodic", "-d", help="Ejecucion codigo sql para dic"),
    formato: str = typer.Option("txt", "--formato", "-f", help="Formato de exportación de resultados"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Nombre base del archivo de salida (sin extensión)"),
    plantilla: Optional[str] = typer.Option(None, "--plantilla", "-t", help="Ruta a plantilla personalizada para formato TXT"),
    comprimir: bool = typer.Option(False, "--comprimir", "-z", help="Comprimir el resultado en formato ZIP"),
    exec_script: Optional[str] = typer.Option(None, "--exe", "-e", help="Ejecutar un fichero python externo")
):
    """
    Herramienta para ejecutar procesos y consultas SQL en Sage50.
    """

    # 1. Ejecución de script externo si se solicita
    if exec_script:
        rprint(Panel(f"[bold blue]Ejecutando script externo:[/bold blue] {exec_script}", title="Info", border_style="blue"))
        try:
            # Ejecuta el script manteniendo el acceso a los módulos instalados
            runpy.run_path(exec_script, run_name="__main__")
        except Exception as e:
            rprint(f"[bold red]Error al ejecutar el script {exec_script}:[/bold red] {e}")
            logging.error(f"Error ejecutando script externo: {e}")

        # Si se ejecuta un script, ¿Deberíamos detenernos o continuar?
        # Asumiremos que es una operación exclusiva salvo que se indiquen otras banderas.
        # Si no hay otras banderas de acción, salimos.
        if not any([reset, sql, sqltodic, clave]):
            rprint("[bold yellow]Fin de ejecución de script externo. Presione una tecla...[/bold yellow]")
            input()
            return

    # 2. Configuración de parámetros para proceso
    para = get_params(
        noupdate=noupdate,
        reset=reset,
        sql=sql,
        clave=clave,
        sqltodic=sqltodic,
        formato=formato,
        output=output,
        plantilla=plantilla,
        comprimir=comprimir
    )

    # 3. Update Check
    try:
        libwertyupdate.update(
            cual="S02", nversion=1.4, autoclose=True, lsilencio=True, update=noupdate
        )
    except Exception as e:
        rprint(f"[yellow]Aviso update:[/yellow] {e}")

    # 4. Inicializar Proceso
    rprint("[dim]Inicializando proceso...[/dim]")
    tarea = proceso.proceso(para)

    try:
        if sqltodic is not None:
            rprint(f"[bold cyan]Ejecutando SQL export a {formato}...[/bold cyan]")
            tarea.sqltodic(
                sqltodic,
                formato=formato,
                nombre_archivo=output,
                plantilla=plantilla,
                comprimir=comprimir,
            )

        if sql is not None:
            rprint("[bold cyan]Ejecutando SQL...[/bold cyan]")
            tarea.sql(sql)

        if reset:
            tarea.reset()
            rprint("[bold red]RESETEADO[/bold red]")

    except Exception as e:
        logging.error(e)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {e}")

    rprint("\n[bold green]Presione UNA tecla para continuar...[/bold green]")

    # Espera a que o usuário pressione uma tecla
    input()

if __name__ == "__main__":
    app()
