import pprint
import sys
from datetime import datetime, timedelta
from pathlib import Path

import libwertyconfig

from exportador_resultados import ExportadorResultados


class proceso:
    def __init__(self, para,api, app="S02"):
        lic = []

        # Función para verificar carencia basada en config.ini

        self.api = api
        self.exportador = ExportadorResultados()
        if not getattr(self.api, "lconecto", False):
            try:
                self.api.confsage50.logger.log.error("No se pudo conectar con SAGE50")
            except AttributeError:
                print("No se pudo conectar con SAGE50")
            return
        base_dir = (
            Path(sys.executable).parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )

        config_path = base_dir / "config.ini"
        try:
            if config_path.exists():


                if libwertyconfig.check_carencia():
                    lic = [True]
                    licencia = "Carencia licencia"
                else:
                    print("Comprobando Licencia")
                    licencia = self.api.extraex50()
                    lic = list(libwertyconfig.x11(licencia=licencia, app=app))
            else:
                print("Falta 'config.ini'.")
                sys.exit(1)

        except OSError as exc:
            try:
                self.api.confsage50.logger.log.warning(f"No se pudo verificar config.ini: {exc}")
            except AttributeError:
                print(f"No se pudo verificar config.ini: {exc}")
        if lic[0]:
            print("-" * 30, "Terminal conectado " + licencia, "+" * 30)
            print("Configuracion en Config.ini")
            pprint.pprint(self.api.confsage50.cvariables)
            print("Tablas en uso GESTION:")
            print(f"Comun  : {self.api.comunes}")
            print(f"Nombre : {self.api.NomComunes}")
            print(f"Letra  : {self.api.letracomu}")
            print(f"Años   : {self.api.obtener_year_letra_nombre_comunes()}")
            # print(f"Version SQL {self.api._connection_manager.get_mssql_version()}")
            print(f"Version SQL {self.api._connection_manager.get_server_version()}")
            if para.clave is not None:
                try:
                    clave_sql = libsage50.generar_contraseña(para.clave)
                    print(f"[OK] Contraseña SQL generada exitosamente: {clave_sql}")
                except ValueError as e:
                    print("[ERROR] ERROR al generar contraseña SQL:")
                    print(f"   {str(e)}")
                    print(f"   Código proporcionado: '{para.clave}'")
                    print('   Uso correcto: s50info.py -clave "TU_CODIGO_LICENCIA"')
                    print('   Ejemplo: s50info.py -clave "SZ012345XD67890S"')
                except Exception as e:
                    print("[ERROR] ERROR inesperado al generar contraseña:")
                    print(f"   {str(e)}")
        else:
            self.api.confsage50.logger.log.error(lic[1])

    def imprimir_diccionarios(
        self,
        lista_diccionarios,
        formato="txt",
        nombre_archivo=None,
        plantilla=None,
        comprimir=False,
    ):
        """
        Método mejorado para exportar resultados en múltiples formatos

        Args:
            lista_diccionarios: Datos a exportar
            formato: Formato de exportación ('txt', 'csv', 'json', 'xml', 'excel')
            nombre_archivo: Nombre base del archivo (opcional)
            plantilla: Ruta a plantilla personalizada (opcional)
            comprimir: Si se debe comprimir el resultado (default: False)
        """
        if not lista_diccionarios:
            print("La lista está vacía")
            return

        try:
            ruta_archivo = self.exportador.exportar(
                datos=lista_diccionarios,
                formato=formato,
                nombre_archivo=nombre_archivo,
                plantilla=plantilla,
                comprimir=comprimir,
                abrir_archivo=True,
            )
            print(f"Resultados exportados a: {ruta_archivo}")
            return True

        except Exception as e:
            print(f"Error al exportar resultados: {e}")
            return False

    def sqltodic(self, sql, formato="txt", nombre_archivo=None, plantilla=None, comprimir=False):
        """
        Ejecuta consulta SQL y exporta resultados

        Args:
            sql: Consulta SQL a ejecutar
            formato: Formato de exportación ('txt', 'csv', 'json', 'xml', 'excel')
            nombre_archivo: Nombre base del archivo (opcional)
            plantilla: Ruta a plantilla personalizada (opcional)
            comprimir: Si se debe comprimir el resultado (default: False)
        """
        query = self.api.build_simple_query(
            sql_template=sql, year=self.api.parse_year_specification("+", self.api.años)[0]
        )
        datos = self.api.sql_to_dict(cursor=self.api.crsr, query=query)
        return self.imprimir_diccionarios(datos, formato, nombre_archivo, plantilla, comprimir)

    def sql(self, sql):
        try:
            revisa=self.api.build_query(sql_template=sql,
                                            years=self.api.SAGE50year("*"))


            self.api.execute_query(revisa,commit=True)
            print("SQL VALIDO:")
            print(revisa)

        except Exception as error:
            print("Fallo en sql")
            print(f"{error}")



