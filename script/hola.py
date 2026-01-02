"""Ejemplo de script externo que usa cliente_sage50."""


proceso.reset_log()
input("pulse para generar el excel")

a=proceso.api.execute_query("""
        select libreria,TEMPSACUMULAT,CONSULTA
 from "EUROWINSYS"."dbo".log_analisis;
                  """)
proceso.imprimir_diccionarios(a,formato="xlsx")
pass
