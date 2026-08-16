"""Ejemplo formativo para revisar y vaciar `log_analisis`.

Uso:
    s50info run script/visualizar_log_analisis_excel_reseteo.py

Que demuestra este ejemplo:
- consulta directa con `proceso.query_to_dict(...)`
- exportacion a Excel con `proceso.imprimir_diccionarios(...)`
- accion operativa posterior con confirmacion manual (`proceso.reset_log()`)

Este ejemplo es util para auditar tiempos y consultas antes de limpiar el log.

Buena practica recomendada:
- lanzar este script siempre desde `s50info run`
- dejar que la aplicacion cargue la configuracion activa en cada ejecucion
- revisar el Excel antes de confirmar el borrado del log
"""


def main():
    datos = proceso.query_to_dict(
        """
        SELECT libreria, TEMPSACUMULAT, CONSULTA
        from "EUROWINSYS".dbo.log_analisis
        """
    )
    print(f"Registros de log recuperados: {len(datos)}")
    proceso.imprimir_diccionarios(datos, formato="xlsx", nombre_archivo="log_analisis")

    confirmacion = input("Desea borrar el log_analisis ahora? (s/N): ").strip().lower()
    if confirmacion in {"s", "si", "y", "yes"}:
        proceso.reset_log()
        print("Log borrado.")
    else:
        print("Log conservado.")


if __name__ == "__main__":
    main()
