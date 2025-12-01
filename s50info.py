import argparse
import logging

import libwertyupdate

import proceso

if __name__ in "__main__":
    parser = argparse.ArgumentParser(
        description="Herramienta para ejecutar sql" + " Mas información en sage50bi@alcatic.es",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-no", "--noupdate", type=str, default=None, help="No actualiza y el motivo"
    )

    parser.add_argument(
        "-r",
        "--reset",
        default=False,
        action="store_true",
        help="Destino de los XML \
                          generados por defecto carpeta .\\resultados",
    )
    parser.add_argument("-s", "--sql", type=str, default=None, help="Ejecucion codigo sql")
    parser.add_argument(
        "-c",
        "--clave",
        type=str,
        default=None,
        help="Obtiene la clave Sage50 sql desde LICENCIA SAGE50",
    )
    parser.add_argument(
        "-d", "--sqltodic", type=str, default=None, help="Ejecucion codigo sql para dic"
    )
    parser.add_argument(
        "-f",
        "--formato",
        type=str,
        default="txt",
        choices=["txt", "csv", "json", "xml", "excel", "xlsx"],
        help="Formato de exportación de resultados",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Nombre base del archivo de salida (sin extensión)",
    )
    parser.add_argument(
        "-t",
        "--plantilla",
        type=str,
        default=None,
        help="Ruta a plantilla personalizada para formato TXT",
    )
    parser.add_argument(
        "-z",
        "--comprimir",
        action="store_true",
        default=False,
        help="Comprimir el resultado en formato ZIP",
    )

    para = parser.parse_args()
    libwertyupdate.update(
        cual="S02", nversion=1.4, autoclose=True, lsilencio=True, update=para.noupdate
    )

    tarea = proceso.proceso(para)
    try:
        if para.sqltodic is not None:
            tarea.sqltodic(
                para.sqltodic,
                formato=para.formato,
                nombre_archivo=para.output,
                plantilla=para.plantilla,
                comprimir=para.comprimir,
            )

        if para.sql is not None:
            tarea.sql(para.sql)

        if para.reset:
            tarea.reset()
            print("RESETEADO")

    except Exception as e:
        logging.error(e)

    print("Presione UNA tecla para continuar...")

    # Espera a que o usuário pressione uma tecla
    input()
