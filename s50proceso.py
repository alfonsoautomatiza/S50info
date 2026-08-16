import logging
import os
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import libwertyconfig
from rich import print as rprint

SAGE50BI_URL = os.getenv("SAGE50BI_URL", "https://sage50eia.com/s50info")


def _default_config_path():
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "s50info" / "config.ini"
    return Path.home() / ".s50info" / "config.ini"


def _abrir_ayuda(url, logger=None):
    """Abre la URL de ayuda y registra el metodo usado y el motivo si falla.

    Usa os.startfile en Windows (via ShellExecute, robusto en builds frozen de
    PyInstaller donde webbrowser.open puede no resolver el navegador) con
    webbrowser.open como fallback. Registra cada intento y, si falla, el motivo.
    """
    log = logger or logging.getLogger("s50proceso")
    if sys.platform == "win32":
        carencia = False
        try:
            os.startfile(url)
            log.info("Ayuda: abierto %s via os.startfile", url)
            return
        except OSError as exc:
            log.warning("Ayuda: os.startfile fallo para %s: %s", url, exc)
            print(f"[Ayuda] os.startfile fallo: {exc}")
    try:
        webbrowser.open(url)
        log.info("Ayuda: abierto %s via webbrowser", url)
    except Exception as exc:
        log.warning("Ayuda: webbrowser.open fallo para %s: %s", url, exc)
        print(f"[Ayuda] webbrowser.open fallo: {exc}")


try:
    from s50exportador_resultados import ExportadorResultados
except Exception as e:
    logging.warning(f"No se pudo cargar ExportadorResultados (hardware/sistema): {e}")
    # Crear un dummy que no falla
    class ExportadorResultados:
        def __init__(self, *args, **kwargs):
            pass
        def exportar(self, *args, **kwargs):
            logging.warning("ExportadorResultados no disponible - exportación deshabilitada")
            return None


class proceso:
    def __init__(self, api, app="SIN", config_path=None, directorio_resultados=None):
        self.lic = []
        self.licencia = {}
        self.crm_status = "unknown"
        self.crm_error = None

        self.api = api
        self.exportador = ExportadorResultados(directorio_resultados or "resultados")

        config_path = Path(config_path) if config_path else _default_config_path()

        # Licencia: se evalua antes del check de conexion para que, aun sin
        # config.ini o sin conectar a SAGE50, x11() pueda solicitar los datos
        # de contacto en la primera ejecucion.
        # Usar el logger de la app (libwertylog) para que las trazas del flujo
        # de contacto lleguen a temp/logError.log; si no esta disponible, usar
        # un logger estandar que propaga al root.
        _lic_proc_log = getattr(getattr(api, "confsage50", None), "logger", None) or logging.getLogger(
            "s50proceso.licencia"
        )
        try:
            config_exists = config_path.exists()
            if config_exists:
                # Periodo de gracia: 7 dias desde la fecha de creacion de config.ini.
                dias_instalacion = max(
                    0,
                    (datetime.now() - datetime.fromtimestamp(config_path.stat().st_ctime)).days,
                )
                carencia = dias_instalacion < 7
                motivo_solicitud_datos = (
                    "config.ini en periodo de carencia; no se solicita formulario"
                    if carencia
                    else "config.ini supera la carencia; se solicita formulario"
                )
            else:
                # Sin config.ini (primera vez): forzar la solicitud de datos.
                dias_instalacion = None
                carencia = False
                motivo_solicitud_datos = "no existe config.ini; se solicita formulario"

            solicitar_datos_localhost = not carencia

            _lic_proc_log.info(
                "[x11] config.ini existe=%s dias_instalacion=%s carencia=%s "
                "solicitar_datos_localhost=%s motivo=%s",
                config_exists,
                dias_instalacion,
                carencia,
                solicitar_datos_localhost,
                motivo_solicitud_datos,
            )
            self.licencia = libwertyconfig.x11(
                licencia=api.lic,
                app=app,
                solicitar_datos_localhost=solicitar_datos_localhost,
                timeout_localhost=30,
                lic_logger=_lic_proc_log,
            )
            _lic_proc_log.info(
                "[x11] resultado -> ok=%s status=%s demo=%s",
                self.licencia.get("ok"),
                self.licencia.get("status"),
                self.licencia.get("demo"),
            )
        except Exception as exc:
            self.licencia = {}
            try:
                _lic_proc_log.warning("[x11] error al evaluar licencia: %s", exc)
            except Exception:
                print(f"[x11] error al evaluar licencia: {exc}")
            try:
                self.api.confsage50.logger.warning(f"Registro Usuario No disponible: {exc}")
            except AttributeError:
                print(f"Registro Usuario No disponible: {exc}")

        # Abrir la pagina de ayuda si la licencia fallo o esta en demo.
        # Fuera del try: si x11() levanto una excepcion, self.licencia queda
        # vacio y de todos modos se intenta abrir la ayuda (registrando el motivo).
        if not carencia and (
            not self.licencia.get("ok")
            or self.licencia.get("demo")
            or self.licencia.get("status") == "demo"
        ):
            _abrir_ayuda(
                SAGE50BI_URL,
                logger=getattr(getattr(self.api, "confsage50", None), "logger", None),
            )

        # Check de conexion a SAGE50: tras el registro de licencia, si no hay
        # conexion no se pueden ejecutar consultas.
        if not getattr(self.api, "lconecto", False):
            try:
                self.api.confsage50.logger.error("No se pudo conectar con SAGE50")
            except AttributeError:
                print("No se pudo conectar con SAGE50")
            return


    def _normalizar_grupo_comunes(self, grupo_comunes):
        if grupo_comunes is None:
            return None

        valor = str(grupo_comunes).strip().upper()
        if not valor:
            return None
        if valor.startswith("COMU"):
            return valor
        if valor.isdigit():
            return f"COMU{int(valor):04d}"
        return valor

    def _resolver_contexto_consulta(self, sqlyear="+", grupo_comunes=None):
        comun = self._normalizar_grupo_comunes(grupo_comunes) or getattr(self.api, "comunes", None)
        years_disponibles = getattr(self.api, "tbyear", None)

        if not isinstance(comun, str):
            comun = None
        if not isinstance(years_disponibles, (list, tuple, str)):
            years_disponibles = None

        if comun and (grupo_comunes is not None or not years_disponibles):
            years_info = self.api.obtener_year_letra_nombre_comunes(comun)
            years_disponibles = (
                years_info[0]
                if isinstance(years_info, (list, tuple)) and years_info
                else years_info
            )
            if not years_disponibles:
                raise ValueError(
                    f"No se pudieron resolver años para el grupo de comunes '{comun}'."
                )

            self.api.comunes = comun
            if isinstance(years_info, (list, tuple)) and len(years_info) > 1:
                self.api.letracomu = years_info[1]
            if isinstance(years_info, (list, tuple)) and len(years_info) > 2:
                self.api.NomComunes = years_info[2]
            self.api.tbyear = years_disponibles

        years_resueltos = self.api.SAGE50year(sqlyear, tyear=years_disponibles)
        if not years_resueltos:
            raise ValueError(
                f"No se encontraron años válidos para sqlyear='{sqlyear}'"
                + (f" en {comun}" if comun else "")
                + "."
            )

        return comun, years_resueltos

    def _formatear_years(self, years):
        if isinstance(years, list):
            return ", ".join(str(year) for year in years)
        return str(years)

    def _sql_en_formato_sage50(self, sql):
        sql_sage50 = re.sub(r"#([A-Za-z_][A-Za-z0-9_]*)\b", r"GESTION!\1", sql)
        sql_sage50 = re.sub(r"\[COMU\]([A-Za-z_][A-Za-z0-9_]*)\b", r"COMUNES!\1", sql_sage50)
        return sql_sage50

    def _split_sql_expressions(self, text):
        partes = []
        actual = []
        profundidad = 0
        in_string = False
        for char in text:
            if char == "'":
                in_string = not in_string
            if in_string:
                actual.append(char)
                continue
            if char == "(":
                profundidad += 1
            elif char == ")" and profundidad > 0:
                profundidad -= 1
            elif char == "," and profundidad == 0:
                partes.append("".join(actual).strip())
                actual = []
                continue
            actual.append(char)
        if actual:
            partes.append("".join(actual).strip())
        return [parte for parte in partes if parte]

    def _quitar_alias(self, expresion):
        expr = expresion.strip()
        return re.sub(r"\s+AS\s+[A-Za-z_][A-Za-z0-9_]*$", "", expr, flags=re.IGNORECASE)

    def _contiene_separador_sentencias(self, sql):
        in_string = False
        in_line_comment = False
        in_block_comment = False
        i = 0
        while i < len(sql):
            char = sql[i]
            nxt = sql[i + 1] if i + 1 < len(sql) else ""
            if in_line_comment:
                if char in "\r\n":
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if char == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if not in_string and char == "-" and nxt == "-":
                in_line_comment = True
                i += 2
                continue
            if not in_string and char == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if char == "'":
                if in_string and nxt == "'":
                    i += 2
                    continue
                in_string = not in_string
            elif char == ";" and not in_string:
                return True
            i += 1
        return False

    def _iter_sql_tokens(self, sql, start_idx=0):
        in_string = False
        in_line_comment = False
        in_block_comment = False
        profundidad = 0
        i = start_idx
        while i < len(sql):
            char = sql[i]
            nxt = sql[i + 1] if i + 1 < len(sql) else ""

            if in_line_comment:
                if char in "\r\n":
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if char == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_string:
                if char == "'":
                    if nxt == "'":
                        i += 2
                        continue
                    in_string = False
                i += 1
                continue

            if char == "-" and nxt == "-":
                in_line_comment = True
                i += 2
                continue
            if char == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if char == "'":
                in_string = True
                i += 1
                continue
            if char == "(":
                profundidad += 1
                i += 1
                continue
            if char == ")":
                if profundidad > 0:
                    profundidad -= 1
                i += 1
                continue
            if char.isalpha() or char == "_":
                inicio = i
                i += 1
                while i < len(sql) and (sql[i].isalnum() or sql[i] == "_"):
                    i += 1
                yield inicio, sql[inicio:i], profundidad
                continue
            i += 1

    def _saltar_espacios(self, sql, idx):
        while idx < len(sql) and sql[idx].isspace():
            idx += 1
        return idx

    def _starts_with_keyword(self, sql, idx, keyword):
        fragment = sql[idx : idx + len(keyword)]
        if fragment.upper() != keyword.upper():
            return False
        before_ok = idx == 0 or not (sql[idx - 1].isalnum() or sql[idx - 1] == "_")
        after_idx = idx + len(keyword)
        after_ok = after_idx >= len(sql) or not (sql[after_idx].isalnum() or sql[after_idx] == "_")
        return before_ok and after_ok

    def _strip_leading_comments(self, sql):
        idx = 0
        while True:
            idx = self._saltar_espacios(sql, idx)
            if sql[idx : idx + 2] == "--":
                fin = sql.find("\n", idx)
                if fin == -1:
                    return ""
                idx = fin + 1
                continue
            if sql[idx : idx + 2] == "/*":
                fin = sql.find("*/", idx + 2)
                if fin == -1:
                    return ""
                idx = fin + 2
                continue
            return sql[idx:]

    def _cte_termina_en_select(self, sql):
        sql = self._strip_leading_comments(sql).strip()
        if not sql.upper().startswith("WITH"):
            return False

        idx = 4
        idx = self._saltar_espacios(sql, idx)
        if self._starts_with_keyword(sql, idx, "RECURSIVE"):
            idx += len("RECURSIVE")
        while idx < len(sql):
            idx = self._saltar_espacios(sql, idx)
            while idx < len(sql) and (sql[idx].isalnum() or sql[idx] in "_[]"):
                idx += 1
            idx = self._saltar_espacios(sql, idx)
            if idx < len(sql) and sql[idx] == "(":
                lookahead = idx + 1
                profundidad = 1
                while lookahead < len(sql) and profundidad > 0:
                    char = sql[lookahead]
                    nxt = sql[lookahead + 1] if lookahead + 1 < len(sql) else ""
                    if char == "'":
                        if nxt == "'":
                            lookahead += 2
                            continue
                        lookahead += 1
                        while lookahead < len(sql):
                            if sql[lookahead] == "'":
                                if lookahead + 1 < len(sql) and sql[lookahead + 1] == "'":
                                    lookahead += 2
                                    continue
                                break
                            lookahead += 1
                    elif char == "-" and nxt == "-":
                        lookahead = sql.find("\n", lookahead)
                        if lookahead == -1:
                            return False
                    elif char == "/" and nxt == "*":
                        fin = sql.find("*/", lookahead + 2)
                        if fin == -1:
                            return False
                        lookahead = fin + 1
                    elif char == "(":
                        profundidad += 1
                    elif char == ")":
                        profundidad -= 1
                    lookahead += 1
                idx = self._saltar_espacios(sql, lookahead)
            if self._starts_with_keyword(sql, idx, "AS"):
                idx += 2
            idx = self._saltar_espacios(sql, idx)
            if idx >= len(sql) or sql[idx] != "(":
                return False

            profundidad = 1
            ultimo_idx = idx
            for ultimo_idx, _, profundidad in self._iter_sql_tokens(sql, idx + 1):
                pass
            idx += 1
            in_string = False
            in_line_comment = False
            in_block_comment = False
            profundidad = 1
            while idx < len(sql) and profundidad > 0:
                char = sql[idx]
                nxt = sql[idx + 1] if idx + 1 < len(sql) else ""
                if in_line_comment:
                    if char in "\r\n":
                        in_line_comment = False
                    idx += 1
                    continue
                if in_block_comment:
                    if char == "*" and nxt == "/":
                        in_block_comment = False
                        idx += 2
                        continue
                    idx += 1
                    continue
                if in_string:
                    if char == "'":
                        if nxt == "'":
                            idx += 2
                            continue
                        in_string = False
                    idx += 1
                    continue
                if char == "-" and nxt == "-":
                    in_line_comment = True
                    idx += 2
                    continue
                if char == "/" and nxt == "*":
                    in_block_comment = True
                    idx += 2
                    continue
                if char == "'":
                    in_string = True
                    idx += 1
                    continue
                if char == "(":
                    profundidad += 1
                elif char == ")":
                    profundidad -= 1
                idx += 1
            if profundidad != 0:
                return False

            idx = self._saltar_espacios(sql, idx)
            if idx < len(sql) and sql[idx] == ",":
                idx += 1
                continue
            break

        idx = self._saltar_espacios(sql, idx)
        return self._starts_with_keyword(sql, idx, "SELECT")

    def _extraer_select_y_from(self, sql):
        sql_strip = self._strip_leading_comments(sql).strip()
        upper = sql_strip.upper()
        if not upper.startswith("SELECT "):
            raise ValueError("--groupby solo soporta consultas SELECT simples.")

        cuerpo = sql_strip[6:]
        cuerpo = cuerpo.lstrip()
        cuerpo_upper = cuerpo.upper()
        if re.match(r"^(DISTINCT|TOP|ALL)\b", cuerpo_upper):
            raise ValueError("--groupby no soporta SELECT DISTINCT, TOP o ALL.")

        idx_from = None
        for i, token, profundidad in self._iter_sql_tokens(cuerpo):
            if profundidad == 0 and token.upper() == "FROM":
                idx_from = i
                break

        if idx_from is None:
            raise ValueError("No se pudo interpretar la consulta para aplicar --groupby.")

        select_clause = cuerpo[:idx_from].strip()
        from_clause = cuerpo[idx_from + 6 :].strip()
        if "SELECT" in select_clause.upper():
            raise ValueError("--groupby no soporta subconsultas en la lista SELECT.")
        return select_clause, from_clause

    def _strip_top_level_clause(self, sql, clause):
        target = clause.upper()
        tokens = target.split()
        for i, token, profundidad in self._iter_sql_tokens(sql):
            if profundidad != 0 or token.upper() != tokens[0]:
                continue
            next_idx = self._saltar_espacios(sql, i + len(token))
            if len(tokens) == 2 and self._starts_with_keyword(sql, next_idx, tokens[1]):
                return sql[:i].strip()
        return sql.strip()

    def _validar_groupby(self, groupby):
        columnas = self._split_sql_expressions(groupby)
        if not columnas:
            raise ValueError("--groupby requiere al menos una columna.")

        patron = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        for col in columnas:
            col_limpia = self._quitar_alias(col)
            if not patron.fullmatch(col_limpia):
                raise ValueError(
                    "--groupby solo admite nombres simples de columna separados por comas."
                )
        return [self._quitar_alias(col) for col in columnas]

    def _construir_query_groupby(self, sql, comun, years, groupby):
        select_clause, from_clause = self._extraer_select_y_from(sql)
        from_clause = self._strip_top_level_clause(from_clause, "GROUP BY")
        from_clause = self._strip_top_level_clause(from_clause, "ORDER BY")

        groupby_cols = self._validar_groupby(groupby)
        select_exprs = self._split_sql_expressions(select_clause)

        inner_cols = []
        for col in groupby_cols:
            if col not in inner_cols:
                inner_cols.append(col)

        agg_pattern = re.compile(
            r"^(MAX|MIN|SUM|AVG|COUNT)\(\s*(.*?)\s*\)$", flags=re.IGNORECASE | re.DOTALL
        )

        for expr in select_exprs:
            expr_sin_alias = self._quitar_alias(expr)
            agg_match = agg_pattern.match(expr_sin_alias)
            if agg_match:
                argumento = agg_match.group(2).strip()
                if argumento == "*":
                    raise ValueError(
                        "--groupby no soporta COUNT(*) todavía. Use una columna explícita."
                    )
                if argumento not in inner_cols:
                    inner_cols.append(argumento)
                continue
            if expr_sin_alias not in inner_cols:
                inner_cols.append(expr_sin_alias)

        inner_sql = f"SELECT {', '.join(inner_cols)} FROM {from_clause}"
        inner_query = self.api.build_query(sql_template=inner_sql, sqlcomun=comun, years=years)
        return f"SELECT {select_clause} FROM ({inner_query}) t GROUP BY {', '.join(groupby_cols)}"

    def _mostrar_configuracion_activa(self):
        rprint("[bold]Configuracion activa:[/bold]")
        cvariables = getattr(self.api.confsage50, "cvariables", {}) or {}
        etiquetas = {
            "api#direccion_servidor": "Servidor SQL",
            "api#driver_servidor": "Driver SQL",
            "api#nombre_usuario": "Usuario SQL",
            "api#password": "Password SQL",
            "api#terminal": "Terminal",
            "api#autenticacion_sql": "Autenticacion SQL",
            "api#comunes": "Grupo comunes",
            "config_sage50#empresa": "Empresa SAGE50",
            "config_sage50#usuario": "Usuario SAGE50",
            "config_sage50#password": "Password SAGE50",
        }

        claves_ordenadas = [clave for clave in etiquetas if clave in cvariables]
        claves_restantes = sorted(clave for clave in cvariables if clave not in etiquetas)

        for clave in [*claves_ordenadas, *claves_restantes]:
            etiqueta = etiquetas.get(clave, clave)
            valor = "********" if clave == "api#password" else cvariables[clave]
            rprint(f"[cyan]{etiqueta}[/cyan]: {valor}")

    def info(self, pausa=True, grupo_comunes=None):
        self._resolver_contexto_consulta(sqlyear="*", grupo_comunes=grupo_comunes)
        # print("-" * 30, "Terminal conectado +" * 30)
        self._mostrar_configuracion_activa()
        print("Tablas en uso GESTION:")
        print(f"Comun  : {self.api.comunes}")
        print(f"Nombre : {self.api.NomComunes}")
        print(f"Letra  : {self.api.letracomu}")
        years = getattr(self.api, "tbyear", None)
        if not years:
            years_info = self.api.obtener_year_letra_nombre_comunes()
            years = (
                years_info[0]
                if isinstance(years_info, (list, tuple)) and years_info
                else years_info
            )
        print(f"Años   : {years}")
        # print(f"Version SQL {self.api._connection_manager.get_mssql_version()}")
        print(f"Version SQL {self.api._connection_manager.get_server_version()}")

    def _log_message(self, level, message):
        try:
            logger = self.api.confsage50.logger
            log_method = getattr(logger, level, None)
            if callable(log_method):
                log_method(message)
                return
        except AttributeError:
            pass

        getattr(logging, level, logging.warning)(message)

    def _es_sql_lectura_permitido(self, sql):
        sql_limpio = self._strip_leading_comments(sql)
        sql_limpio = re.sub(r"^[\s(]+", "", sql_limpio)
        sql_upper = sql_limpio.upper().strip()
        if self._contiene_separador_sentencias(sql_limpio):
            return False
        if sql_upper.startswith("WITH"):
            return self._cte_termina_en_select(sql_limpio)
        return sql_upper.startswith("SELECT")

    def _obtener_credenciales_crm(self):
        """Consulta PRIVATEKEY y PUBLICKEY de FMCRM0{letracomu}.dbo.credenciales.

        Returns:
            dict con PRIVATEKEY y PUBLICKEY, o None si no existe la base/tabla.
        """
        self.crm_status = "unavailable"
        self.crm_error = None
        try:
            letracomu = getattr(self.api, "letracomu", "")
            if not letracomu:
                self.crm_error = "Sin letra de comunes"
                return None

            db_name = f"FMCRM0{letracomu}"
            query = f'SELECT PRIVATEKEY, PUBLICKEY FROM "{db_name}"."dbo"."credenciales"'
            datos = self.api.sql_to_list(query=query, as_dict=True)

            if datos and len(datos) > 0:
                self.crm_status = "available"
                return datos[0]
            self.crm_error = "Tabla credenciales sin registros"
            return None
        except Exception as exc:
            mensaje = str(exc).lower()
            missing_markers = (
                "invalid object name",
                "cannot open database",
                "does not exist",
                "no such table",
                "unknown object",
                "credenciales",
                "fmcrm0",
            )
            if any(marker in mensaje for marker in missing_markers):
                self.crm_error = str(exc)
                return None

            self.crm_status = "error"
            self.crm_error = str(exc)
            try:
                self.api.confsage50.logger.warning(f"Error consultando credenciales CRM: {exc}")
            except AttributeError:
                print(f"Error consultando credenciales CRM: {exc}")
            return None

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

    def sql2doc(
        self,
        sql,
        sqlyear="+",
        grupo_comunes=None,
        groupby=None,
        sage50=False,
        formato="txt",
        nombre_archivo=None,
        plantilla=None,
        comprimir=False,
    ):
        """
        Ejecuta consulta SQL y exporta resultados

        Args:
            sql: Consulta SQL a ejecutar
            formato: Formato de exportación ('txt', 'csv', 'json', 'xml', 'excel')
            nombre_archivo: Nombre base del archivo (opcional)
            plantilla: Ruta a plantilla personalizada (opcional)
            comprimir: Si se debe comprimir el resultado (default: False)
        """
        if not self._es_sql_lectura_permitido(sql):
            mensaje = (
                "Consulta no permitida: S50Info solo permite consultas SQL de lectura "
                "(SELECT o WITH). No se exportan sentencias de escritura."
            )
            self._log_message("error", mensaje)
            print(mensaje)
            return False

        comun, years = self._resolver_contexto_consulta(
            sqlyear=sqlyear, grupo_comunes=grupo_comunes
        )
        print(f"Grupo comunes: {comun}")
        print(f"Años resueltos: {self._formatear_years(years)}")
        if groupby:
            print(f"Agrupacion final: {groupby}")
        if sage50:
            print("SQL SAGE50:")
            print(self._sql_en_formato_sage50(sql))
        inicio = time.perf_counter()
        if groupby and isinstance(years, list) and len(years) > 1:
            query = self._construir_query_groupby(sql, comun, years, groupby)
        else:
            query = self.api.build_query(sql_template=sql, sqlcomun=comun, years=years)
        datos = self.api.sql_to_list(query=query, as_dict=True)
        print(f"Tiempo consulta: {time.perf_counter() - inicio:.3f}s")
        return self.imprimir_diccionarios(datos, formato, nombre_archivo, plantilla, comprimir)

    def sql(self, sql, sqlyear="+", grupo_comunes=None, groupby=None, sage50=False):
        try:
            if not self._es_sql_lectura_permitido(sql):
                mensaje = (
                    "Consulta no permitida: S50Info solo permite consultas SQL de lectura "
                    "(SELECT o WITH). No se ejecutan sentencias de escritura."
                )
                self._log_message("error", mensaje)
                print(mensaje)
                return False

            comun, years = self._resolver_contexto_consulta(
                sqlyear=sqlyear, grupo_comunes=grupo_comunes
            )
            print(f"Grupo comunes: {comun}")
            print(f"Años resueltos: {self._formatear_years(years)}")
            if groupby:
                print(f"Agrupacion final: {groupby}")
            if sage50:
                print("SQL SAGE50:")
                print(self._sql_en_formato_sage50(sql))
            inicio = time.perf_counter()
            if groupby and isinstance(years, list) and len(years) > 1:
                revisa = self._construir_query_groupby(sql, comun, years, groupby)
            else:
                revisa = self.api.build_query(sql_template=sql, sqlcomun=comun, years=years)

            self.api.execute_query(revisa, commit=False)
            print(f"Tiempo consulta: {time.perf_counter() - inicio:.3f}s")
            print("SQL VALIDO:")
            print(revisa)
            return True

        except Exception as error:
            print("Fallo en sql")
            print(f"{error}")
            return False

    def reset_log(self):
        self.api.execute_query('truncate table "EUROWINSYS"."dbo".log_analisis;', commit=True)
        self.api.execute_query('truncate table "EUROWINSYS"."dbo".log_error;', commit=True)
