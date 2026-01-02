import logging
import runpy
from pathlib import Path
from types import SimpleNamespace

import libsage50

# Local imports
import libwertyupdate
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

import proceso

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="""S50Info - Herramienta de administración para bases de datos Sage50

Permite ejecutar consultas SQL, scripts Python, y operaciones de mantenimiento sobre bases de datos Sage50.
"""
)
console = Console()


def get_params(**kwargs):
    """Crea un objeto compatible con argparse.Namespace para pasar a proceso"""
    return SimpleNamespace(**kwargs)


@app.command()
def main(
    # script: str | None = typer.Argument(
    #     None, help="Ejecutar script/carpeta Python (archivo .py o carpeta con scripts)"
    # ),
    noupdate: str | None = typer.Option(None, "--noupdate", "-no", help="No actualiza y el motivo"),
    sql: str | None = typer.Option(None, "--sql", "-s", help="Ejecucion codigo sql"),
    clave: str | None = typer.Option(
        None, "--clave", "-c", help="Obtiene la clave Sage50 sql desde LICENCIA SAGE50"
    ),
    sqltodic: str | None = typer.Option(
        None, "--sql2doc", "-d", help="Ejecucion codigo sql para dic"
    ),
    formato: str = typer.Option(
        "txt", "--formato", "-f", help="Formato de exportación de resultados"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Nombre base del archivo de salida (sin extensión)"
    ),
    plantilla: str | None = typer.Option(
        None, "--plantilla", "-t", help="Ruta a plantilla personalizada para formato TXT"
    ),
    comprimir: bool = typer.Option(
        False, "--comprimir", "-z", help="Comprimir el resultado en formato ZIP"
    ),
    exec_script: str | None = typer.Option(
        None, "--exe", "-e", help="Ejecutar un fichero python externo"
    ),
    reset_log: str | None = typer.Option(
        None, "--reset", "-r", help="Ejecutar un fichero python externo"
    ),
):
    """
    ===============================================================================
    EJECUCION DE PROCESOS Y CONSULTAS SQL EN SAGE50
    ===============================================================================

    Esta herramienta permite realizar multiples operaciones sobre bases de datos Sage50:

    -------------------------------------------------------------------------------
    FUNCIONALIDADES PRINCIPALES:
    -------------------------------------------------------------------------------

    - Ejecucion de consultas SQL (--sql, -s)
      Ejecuta codigo SQL y muestra resultados por pantalla

    - Exportacion de SQL a diferentes formatos (--sqltodic, -d)
      Exporta resultados a TXT (con plantillas), Excel, JSON, CSV, HTML
      Opciones de formato: txt, xlsx, json, csv, html

    - Obtencion de clave SQL Sage50 (--clave, -c)
      Recupera la clave de acceso SQL desde la licencia de SAGE50

    - Ejecucion de scripts Python externos (--exe, -e)
      Permite ejecutar archivos .py o carpetas con scripts personalizados
      Los scripts tienen acceso al objeto 'proceso' para interactuar con SAGE50

    - Control de actualizaciones (--noupdate, -no)
      Desactiva la verificacion de actualizaciones y especifica el motivo

    -------------------------------------------------------------------------------
    FORMATOS DE EXPORTACION:
    -------------------------------------------------------------------------------
      --formato, -f : txt (default) | xlsx | json | csv | html
      --output, -o  : Nombre base del archivo de salida (sin extension)
      --plantilla, -t : Ruta a plantilla personalizada para formato TXT
      --comprimir, -z : Comprime el resultado en formato ZIP

    -------------------------------------------------------------------------------
    EJEMPLOS DE USO:
    -------------------------------------------------------------------------------

      # obtiene una consulta SQL en formato SAGE50 para el comunes activo.
      s50info --sql "SELECT * FROM GESTION!CLIENTES"

      # Exportar SQL a Excel
      s50info --sql2doc "SELECT * FROM ARTICULOS" --formato xlsx --output articulos

      # Exportar con plantilla personalizada y comprimir
      s50info -d "SELECT * FROM ALBARANES" -f txt -t plantilla.txt -o reporte -z

      # Obtener clave SQL de SAGE50
      s50info --clave

      # Ejecutar script Python externo
      s50info --exe mi_script.py

      # Ejecutar todos los scripts de una carpeta
      s50info --exe ./mis_scripts/

      # Desactivar actualizaciones
      s50info --sql "SELECT 1" --noupdate "En desarrollo"

    -------------------------------------------------------------------------------
    ARCHIVOS DE CONFIGURACION:
    -------------------------------------------------------------------------------
      config.ini : Parametros de conexion a base de datos (servidor, credenciales, ODBC)

    -------------------------------------------------------------------------------
    REQUISITOS:
    -------------------------------------------------------------------------------
      - Conexion activa a SAGE50
      - Credenciales validas de SQL Server


    """

    # 0. Crear objeto API (PRIMERO - requisito para todo)
    api_obj = None
    try:
        rprint("[dim]Conectando a SAGE50...[/dim]")
        api_obj = libsage50.apiSAGE50(carencia_check=True, app="S02")
        if not getattr(api_obj, "lconecto", False):
            rprint("[bold red]Error:[/bold red] No se pudo conectar con SAGE50")
            return
        rprint("[green]✓ Conectado a SAGE50[/green]")
    except Exception as e:
        rprint(f"[bold red]Error al conectar con SAGE50:[/bold red] {e}")
        logging.error(f"Error conectando SAGE50: {e}")
        return

    # 1. Ejecución de script externo si se solicita
    if exec_script:
        # Validar que no esté vacío o con solo espacios
        if not exec_script.strip():
            rprint("[bold red]Error:[/bold red] No se especificó ninguna ruta para --exe")
            return

        # Validar ruta
        path = Path(exec_script.strip())

        # Verificar si la ruta existe
        if not path.exists():
            # Resolver ruta absoluta para mostrar dónde se buscó
            abs_path = path.resolve()
            rprint(f"[bold red]Error:[/bold red] No se encontró: '{exec_script}'")
            rprint(f"[dim]Buscando en:[/dim] {abs_path}")
            return

        # Crear objeto proceso para pasarlo al script
        rprint("[dim]Inicializando proceso...[/dim]")
        para = get_params(
            noupdate=noupdate,
            sql=sql,
            clave=clave,
            sqltodic=sqltodic,
            formato=formato,
            output=output,
            plantilla=plantilla,
            comprimir=comprimir,
        )
        proceso_obj = proceso.proceso(para, api=api_obj)

        # Si es un directorio, ejecutar todos los archivos .py
        if path.is_dir():
            rprint(
                Panel(
                    f"[bold blue]Ejecutando scripts de carpeta:[/bold blue] {exec_script}",
                    title="Info",
                    border_style="blue",
                )
            )

            # Buscar todos los archivos .py en la carpeta
            py_files = sorted(path.glob("*.py"))

            if not py_files:
                rprint(f"[yellow]Aviso:[/yellow] No se encontraron archivos .py en '{exec_script}'")
                return

            # Ejecutar cada archivo Python
            for script_file in py_files:
                rprint(f"[cyan]Ejecutando:[/cyan] {script_file.name}")
                try:
                    script_globals = {
                        "__name__": "__main__",
                        "__file__": str(script_file),
                        "proceso": proceso_obj,
                    }
                    runpy.run_path(
                        str(script_file), init_globals=script_globals, run_name="__main__"
                    )
                except Exception as e:
                    rprint(f"[bold red]Error al ejecutar {script_file.name}:[/bold red] {e}")
                    logging.error(f"Error ejecutando script externo: {e}")

        # Si es un archivo, verificar que sea .py y ejecutarlo
        elif path.is_file():
            # Validar que sea un archivo Python
            if path.suffix != ".py":
                rprint(
                    f"[bold red]Error:[/bold red] El archivo '{exec_script}' no es un archivo Python (.py)"
                )
                return

            rprint(
                Panel(
                    f"[bold blue]Ejecutando script externo:[/bold blue] {exec_script}",
                    title="Info",
                    border_style="blue",
                )
            )
            try:
                script_globals = {
                    "__name__": "__main__",
                    "__file__": exec_script,
                    "proceso": proceso_obj,
                }
                runpy.run_path(exec_script, init_globals=script_globals, run_name="__main__")
            except Exception as e:
                rprint(f"[bold red]Error al ejecutar el script {exec_script}:[/bold red] {e}")
                logging.error(f"Error ejecutando script externo: {e}")

        # Si se ejecuta un script, terminar sin más acciones
        return

    # 2. Configuración de parámetros para proceso
    para = get_params(
        noupdate=noupdate,
        sql=sql,
        clave=clave,
        sqltodic=sqltodic,
        formato=formato,
        output=output,
        plantilla=plantilla,
        comprimir=comprimir,
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
    tarea = proceso.proceso(para, api=api_obj)

    try:
        if sqltodic is not None:
            rprint(f"[bold cyan]Ejecutando SQL export a {formato}...[/bold cyan]")
            tarea.sql2doc(
                sqltodic,
                formato=formato,
                nombre_archivo=output,
                plantilla=plantilla,
                comprimir=comprimir,
            )

        if sql is not None:
            rprint("[bold cyan]Obteniendo SQL...[/bold cyan]")
            tarea.sql(sql)

    except Exception as e:
        logging.error(e)
        rprint(f"[bold red]Error durante el proceso:[/bold red] {e}")

    rprint("\n[bold green]Presione UNA tecla para continuar...[/bold green]")

    # Espera a que o usuário pressione uma tecla
    input()


if __name__ == "__main__":
    app()
