"""Ejemplo de script externo que usa cliente_sage50."""

api.execute_query("""
TRUNCATE TABLE [eurowinsys].[dbo].[log_analisis];
TRUNCATE TABLE [eurowinsys].[dbo].[log_error];
                  """)


api.execute_query("""
                  """)
