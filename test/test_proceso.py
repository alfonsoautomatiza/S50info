"""
Tests para el módulo proceso.py
"""

from unittest.mock import MagicMock, patch

import sys

import pytest


# Mock de dependencias antes de importar
mock_libsage50 = MagicMock()
mock_libwertyconfig = MagicMock()
mock_docx = MagicMock()
mock_rich = MagicMock()
mock_webbrowser = MagicMock()
mock_libwertyconfig.x11.return_value = {"ok": True, "status": "valid", "data": {}, "demo": False}

with patch.dict(
    "sys.modules",
    {
        "libsage50": mock_libsage50,
        "libwertyconfig": mock_libwertyconfig,
        "docx": mock_docx,
        "rich": mock_rich,
        "webbrowser": mock_webbrowser,
    },
):
    import s50proceso
    from s50proceso import proceso, SAGE50BI_URL

# patch.dict restaura sys.modules al salir, borrando s50proceso del cache;
# reinsertarlo permite que @patch("s50proceso.*") resuelva el módulo sin
# re-importarlo (lo que fallaría sin los mocks de libwertyconfig en sys.modules).
sys.modules["s50proceso"] = s50proceso


@pytest.fixture(autouse=True)
def _config_ini_stub(monkeypatch):
    """proceso.__init__ exige config.ini; no depender del FS real (CI/checkout limpio)."""
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    fake_stat = MagicMock()
    fake_stat.st_ctime = 0.0
    monkeypatch.setattr("pathlib.Path.stat", lambda self, *args, **kwargs: fake_stat)
    # proceso.__init__ instancia ExportadorResultados, que hace mkdir sobre el
    # FS real; parchearlo evita depender de carpetas existentes en el checkout.
    # Usar el objeto módulo capturado: patch.dict borra s50proceso de sys.modules
    # al salir del bloque, por lo que una ruta str re-importaría sin los mocks.
    monkeypatch.setattr(s50proceso, "ExportadorResultados", MagicMock())


class TestObtenerCredencialesCrm:
    """Tests para el método _obtener_credenciales_crm"""

    @pytest.fixture
    def mock_api(self):
        """Fixture para mock de API"""
        api = MagicMock()
        api.letracomu = "A"
        api.crsr = MagicMock()
        return api

    def test_obtener_credenciales_crm_success(self, mock_api):
        """Test consulta exitosa que devuelve credenciales"""
        # Configurar proceso con mock de API
        mock_api.sql_to_list.return_value = [{"PRIVATEKEY": "key123", "PUBLICKEY": "pub456"}]

        proc = proceso(api=mock_api)

        # Ejecutar
        resultado = proc._obtener_credenciales_crm()

        # Verificar
        assert resultado is not None
        assert resultado["PRIVATEKEY"] == "key123"
        assert resultado["PUBLICKEY"] == "pub456"

        # Verificar que se llamó a sql_to_list
        mock_api.sql_to_list.assert_called_once()
        call_args = mock_api.sql_to_list.call_args
        assert "FMCRM0A" in call_args[1]["query"]
        assert "credenciales" in call_args[1]["query"]

    def test_obtener_credenciales_crm_no_letracomu(self, mock_api):
        """Test sin letracomu configurado"""
        mock_api.letracomu = ""

        proc = proceso(api=mock_api)

        # Ejecutar
        resultado = proc._obtener_credenciales_crm()

        # Verificar
        assert resultado is None
        # No debe llamar a sql_to_list
        mock_api.sql_to_list.assert_not_called()

    def test_obtener_credenciales_crm_query_exception(self, mock_api):
        """Test manejo de excepción en query"""
        mock_api.sql_to_list.side_effect = Exception("Error de conexión")

        proc = proceso(api=mock_api)

        # Ejecutar
        resultado = proc._obtener_credenciales_crm()

        # Verificar
        assert resultado is None

    def test_obtener_credenciales_crm_empty_result(self, mock_api):
        """Test cuando query devuelve lista vacía"""
        mock_api.sql_to_list.return_value = []

        proc = proceso(api=mock_api)

        # Ejecutar
        resultado = proc._obtener_credenciales_crm()

        # Verificar
        assert resultado is None


class TestInfo:
    """Tests para el método info"""

    @pytest.fixture
    def mock_api_with_config(self):
        """Fixture para mock de API con configuración"""
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        api.confsage50.cvariables = {"server": "MYSERVER"}
        api.comunes = "EUROWINSYS"
        api.NomComunes = "Comun principal"
        api.letracomu = "A"
        api.tbyear = ["2023"]
        mock_conn_mgr = MagicMock()
        mock_conn_mgr.get_server_version.return_value = "15.0.2000.5"
        api._connection_manager = mock_conn_mgr
        return api

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_info_prints_connection_info(self, mock_print, mock_input, mock_api_with_config):
        """Test que info imprime información de conexión"""
        proc = proceso(api=mock_api_with_config)
        proc.lic = [True]
        proc.licencia = "Licencia válida"

        # Ejecutar
        proc.info()

        # Verificar que se llamó a print
        assert mock_print.called
        # Verificar que se imprimió la configuración
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Tablas en uso GESTION" in call for call in print_calls)

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_info_applies_grupo_comunes_override(
        self, mock_print, mock_input, mock_api_with_config
    ):
        mock_api_with_config.obtener_year_letra_nombre_comunes.return_value = (
            ["2024JX", "2025JX"],
            "JX",
            "Grupo 4",
        )
        proc = proceso(api=mock_api_with_config)
        proc.lic = [True]
        proc.licencia = "Licencia válida"

        proc.info(grupo_comunes="4")

        mock_api_with_config.obtener_year_letra_nombre_comunes.assert_called_once_with("COMU0004")
        assert mock_api_with_config.comunes == "COMU0004"

    @patch("builtins.input")
    @patch("builtins.print")
    def test_info_without_pause_does_not_wait(self, mock_print, mock_input, mock_api_with_config):
        """Test que info no pausa cuando se indica pausa=False"""
        proc = proceso(api=mock_api_with_config)
        proc.lic = [True]
        proc.licencia = "Licencia válida"

        proc.info(pausa=False)

        assert mock_print.called
        mock_input.assert_not_called()

    @patch("s50proceso.rprint")
    def test_configuracion_activa_enmascara_password_sql(
        self, mock_rprint, mock_api_with_config
    ):
        mock_api_with_config.confsage50.cvariables = {
            "api#nombre_usuario": "sa",
            "api#password": "super-secret",
        }
        proc = proceso(api=mock_api_with_config)

        proc._mostrar_configuracion_activa()

        output = "\n".join(str(call.args[0]) for call in mock_rprint.call_args_list)
        assert "Password SQL" in output
        assert "********" in output
        assert "super-secret" not in output

    @patch("s50proceso.rprint")
    def test_configuracion_activa_password_vacia_no_muestra_asteriscos(
        self, mock_rprint, mock_api_with_config
    ):
        """Sin contraseña configurada no debe fingir que la hay con ********."""
        mock_api_with_config.confsage50.cvariables = {
            "api#nombre_usuario": "sa",
            "api#password": "",
        }
        proc = proceso(api=mock_api_with_config)

        proc._mostrar_configuracion_activa()

        output = "\n".join(str(call.args[0]) for call in mock_rprint.call_args_list)
        assert "Password SQL" in output
        assert "********" not in output
        assert "(sin definir)" in output

    @patch("s50proceso.rprint")
    def test_configuracion_activa_escapa_markup_del_valor(
        self, mock_rprint, mock_api_with_config, monkeypatch
    ):
        """El valor dinámico pasa por el escape de markup rich antes de rprint."""
        monkeypatch.setattr(
            s50proceso, "_rich_escape", lambda texto: f"<ESC>{texto}</ESC>"
        )
        mock_api_with_config.confsage50.cvariables = {
            "api#direccion_servidor": "[Microsoft][ODBC Driver 17]",
        }
        proc = proceso(api=mock_api_with_config)

        proc._mostrar_configuracion_activa()

        output = "\n".join(str(call.args[0]) for call in mock_rprint.call_args_list)
        assert "<ESC>[Microsoft][ODBC Driver 17]</ESC>" in output

    @patch("s50proceso.rprint")
    def test_configuracion_activa_enmascara_password_sage50(
        self, mock_rprint, mock_api_with_config
    ):
        mock_api_with_config.confsage50.cvariables = {
            "config_sage50#empresa": "MiEmpresa",
            "config_sage50#password": "secreto-sage50",
        }
        proc = proceso(api=mock_api_with_config)

        proc._mostrar_configuracion_activa()

        output = "\n".join(str(call.args[0]) for call in mock_rprint.call_args_list)
        assert "Password SAGE50" in output
        assert "********" in output
        assert "secreto-sage50" not in output

    @patch("s50proceso.rprint")
    def test_configuracion_activa_enmascara_cualquier_clave_password(
        self, mock_rprint, mock_api_with_config
    ):
        secretos = {
            "api#password": "secreto-sql-9Z",
            "config_sage50#password": "secreto-sage-8Y",
            "otra#Password_Webhook": "secreto-hook-7X",
        }
        mock_api_with_config.confsage50.cvariables = {
            **secretos,
            "api#terminal": "C:\\Sage\\Term01",
        }
        proc = proceso(api=mock_api_with_config)

        proc._mostrar_configuracion_activa()

        output = "\n".join(str(call.args[0]) for call in mock_rprint.call_args_list)
        for secreto in secretos.values():
            assert secreto not in output
        assert "********" in output
        assert "C:\\Sage\\Term01" in output


class TestImprimirDiccionarios:
    """Tests para el método imprimir_diccionarios"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        return api

    @patch("builtins.print")
    def test_imprimir_diccionarios_empty_list(self, mock_print, mock_api):
        """Test con lista vacía"""
        proc = proceso(api=mock_api)

        # Ejecutar
        resultado = proc.imprimir_diccionarios([])

        # Verificar
        assert resultado is None  # El método no retorna nada explícitamente para lista vacía
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("La lista está vacía" in call for call in print_calls)

    @patch("builtins.print")
    def test_imprimir_diccionarios_success(self, mock_print, mock_api):
        """Test exportación exitosa"""
        mock_exportador = MagicMock()
        mock_exportador.exportar.return_value = "resultados/test.txt"

        proc = proceso(api=mock_api)
        proc.exportador = mock_exportador
        datos = [{"col1": "val1", "col2": "val2"}]

        # Ejecutar
        resultado = proc.imprimir_diccionarios(datos)

        # Verificar
        assert resultado is True
        mock_exportador.exportar.assert_called_once()


class TestSql:
    """Tests para el método sql"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        api.build_query.return_value = "SELECT * FROM TEST"
        return api

    @patch("builtins.print")
    def test_sql_success(self, mock_print, mock_api):
        """Test ejecución SQL exitosa"""
        proc = proceso(api=mock_api)

        # Ejecutar
        proc.sql("SELECT * FROM TEST")

        # Verificar
        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("SQL VALIDO" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_uses_requested_sqlyear(self, mock_print, mock_api):
        """Test que sql usa el año solicitado."""
        mock_api.SAGE50year.return_value = ["2025JX"]
        proc = proceso(api=mock_api)

        proc.sql("SELECT * FROM TEST", sqlyear="2025JX")

        mock_api.SAGE50year.assert_called_once_with("2025JX", tyear=None)
        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT * FROM TEST", sqlcomun=None, years=["2025JX"]
        )

    @pytest.mark.parametrize(
        ("sqlyear", "resolved_years"),
        [
            ("+", ["2026JX"]),
            ("*", ["2024JX", "2025JX", "2026JX"]),
            ("2025JX", ["2025JX"]),
            ("2024JX,2025JX", ["2024JX", "2025JX"]),
        ],
    )
    @patch("builtins.print")
    def test_sql_accepts_all_sqlyear_variants(self, mock_print, mock_api, sqlyear, resolved_years):
        """Test de todas las variantes soportadas por --sqlyear en sql."""
        mock_api.SAGE50year.return_value = resolved_years
        proc = proceso(api=mock_api)

        proc.sql("SELECT * FROM TEST", sqlyear=sqlyear)

        mock_api.SAGE50year.assert_called_once_with(sqlyear, tyear=None)
        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT * FROM TEST", sqlcomun=None, years=resolved_years
        )
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_rejects_non_select_queries(self, mock_print, mock_api):
        """Test que bloquea sentencias de escritura"""
        proc = proceso(api=mock_api)

        # Ejecutar
        proc.sql("DELETE FROM CLIENTES")

        # Verificar
        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        mock_api.confsage50.logger.error.assert_called_once()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_rejects_multi_statement_queries(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("SELECT 1; DROP TABLE CLIENTES")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_rejects_with_delete_queries(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("WITH cte AS (SELECT * FROM CLIENTES) DELETE FROM cte")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_allows_semicolon_inside_comment(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("SELECT * FROM TEST /* comentario ; seguro */")

        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_allows_semicolon_inside_line_comment(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("SELECT * FROM TEST -- comentario ; seguro\n")

        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_allows_semicolon_inside_string_literal(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("SELECT ';' AS TEXTO FROM TEST")

        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_allows_valid_with_select_cte(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("WITH cte AS (SELECT * FROM CLIENTES) SELECT * FROM cte")

        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_rejects_with_delete_bypass_using_comment(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        proc.sql("WITH cte AS (SELECT * FROM X /* ) SELECT */ ) DELETE FROM cte")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @pytest.mark.parametrize(
        "consulta",
        [
            "SELECT * INTO t FROM CLIENTES",
            "select codigo into copia from clientes",
            "WITH cte AS (SELECT 1 AS x) SELECT x INTO y FROM cte",
            "SELECT * FROM /* into */ TEST; SELECT 1 INTO t FROM TEST",
        ],
    )
    @patch("builtins.print")
    def test_sql_rejects_select_into(self, mock_print, mock_api, consulta):
        """SELECT ... INTO crea tablas: debe rechazarse como escritura."""
        proc = proceso(api=mock_api)

        proc.sql(consulta)

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @pytest.mark.parametrize(
        "consulta",
        [
            "SELECT 'drop into nothing' FROM TEST",
            "SELECT INTO_X FROM TEST",
            "SELECT * FROM TEST /* comentario into seguro */",
        ],
    )
    @patch("builtins.print")
    def test_sql_allows_into_no_relevante(self, mock_print, mock_api, consulta):
        """'into' en string, identificador INTO_X o comentario no es escritura."""
        proc = proceso(api=mock_api)

        proc.sql(consulta)

        mock_api.build_query.assert_called_once()
        mock_api.execute_query.assert_called_once_with("SELECT * FROM TEST", commit=False)

    @patch("builtins.print")
    def test_sql_applies_grupo_comunes_override(self, mock_print, mock_api):
        mock_api.obtener_year_letra_nombre_comunes.return_value = (
            ["2024JX", "2025JX"],
            "JX",
            "Grupo 4",
        )
        mock_api.SAGE50year.return_value = ["2025JX"]
        proc = proceso(api=mock_api)

        proc.sql("SELECT * FROM TEST", sqlyear="+", grupo_comunes="4")

        mock_api.obtener_year_letra_nombre_comunes.assert_called_once_with("COMU0004")
        mock_api.SAGE50year.assert_called_once_with("+", tyear=["2024JX", "2025JX"])
        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT * FROM TEST", sqlcomun="COMU0004", years=["2025JX"]
        )

    def test_sql_groupby_wraps_union_query(self, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX", "2019JX"]
        mock_api.build_query.return_value = (
            '(SELECT CODIGO, NOMBRE FROM "2017JX".dbo.clientes) UNION ALL '
            '(SELECT CODIGO, NOMBRE FROM "2018JX".dbo.clientes) UNION ALL '
            '(SELECT CODIGO, NOMBRE FROM "2019JX".dbo.clientes)'
        )
        proc = proceso(api=mock_api)

        proc.sql("select CODIGO, MAX(NOMBRE) from #clientes", sqlyear="@", groupby="CODIGO")

        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT CODIGO, NOMBRE FROM #clientes",
            sqlcomun=None,
            years=["2017JX", "2018JX", "2019JX"],
        )
        executed_query = mock_api.execute_query.call_args.args[0]
        assert "FROM ((SELECT CODIGO, NOMBRE FROM" in executed_query
        assert "GROUP BY CODIGO" in executed_query

    @patch("builtins.print")
    def test_sql_groupby_rejects_invalid_identifier(self, mock_print, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX"]
        proc = proceso(api=mock_api)

        proc.sql("select CODIGO, MAX(NOMBRE) from #clientes", sqlyear="@", groupby="CODIGO;DROP")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("solo admite nombres simples de columna" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_groupby_rejects_select_top(self, mock_print, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX"]
        proc = proceso(api=mock_api)

        proc.sql("select top 10 CODIGO, MAX(NOMBRE) from #clientes", sqlyear="@", groupby="CODIGO")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("no soporta SELECT DISTINCT, TOP o ALL" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_groupby_rejects_select_top_with_double_space(self, mock_print, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX"]
        proc = proceso(api=mock_api)

        proc.sql("select  top 10 CODIGO, MAX(NOMBRE) from #clientes", sqlyear="@", groupby="CODIGO")

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("no soporta SELECT DISTINCT, TOP o ALL" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql_groupby_rejects_subquery_in_select(self, mock_print, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX"]
        proc = proceso(api=mock_api)

        proc.sql(
            "select CODIGO, (select MAX(X) from OTRA) as MX from #clientes",
            sqlyear="@",
            groupby="CODIGO",
        )

        mock_api.build_query.assert_not_called()
        mock_api.execute_query.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("no soporta subconsultas en la lista SELECT" in call for call in print_calls)

    def test_sql_groupby_accepts_newline_before_from(self, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX"]
        mock_api.build_query.return_value = (
            '(SELECT CODIGO, NOMBRE FROM "2017JX".dbo.clientes) UNION ALL '
            '(SELECT CODIGO, NOMBRE FROM "2018JX".dbo.clientes)'
        )
        proc = proceso(api=mock_api)

        proc.sql("select CODIGO, MAX(NOMBRE)\nfrom #clientes", sqlyear="@", groupby="CODIGO")

        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT CODIGO, NOMBRE FROM #clientes",
            sqlcomun=None,
            years=["2017JX", "2018JX"],
        )


class TestSql2Doc:
    """Tests para el método sql2doc"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        api.SAGE50year.return_value = ["2026JX"]
        api.build_query.return_value = 'SELECT * FROM "2026JX".dbo.clientes'
        api.crsr = MagicMock()
        api.sql_to_list.return_value = [{"CLIENTE": "ACME"}]
        return api

    def test_sql2doc_uses_build_query_with_single_year(self, mock_api):
        proc = proceso(api=mock_api)
        proc.imprimir_diccionarios = MagicMock(return_value=True)

        result = proc.sql2doc("select * from #clientes", sqlyear="+", formato="txt")

        assert result is True
        mock_api.SAGE50year.assert_called_once_with("+", tyear=None)
        mock_api.build_query.assert_called_once_with(
            sql_template="select * from #clientes", sqlcomun=None, years=["2026JX"]
        )
        mock_api.sql_to_list.assert_called_once_with(
            query='SELECT * FROM "2026JX".dbo.clientes', as_dict=True
        )
        proc.imprimir_diccionarios.assert_called_once_with(
            [{"CLIENTE": "ACME"}], "txt", None, None, False
        )

    @pytest.mark.parametrize(
        ("sqlyear", "resolved_years", "expected_year"),
        [
            ("+", ["2026JX"], "2026JX"),
            ("*", ["2024JX", "2025JX", "2026JX"], "2024JX"),
            ("2025JX", ["2025JX"], "2025JX"),
            ("2024JX,2025JX", ["2024JX", "2025JX"], "2024JX"),
        ],
    )
    def test_sql2doc_accepts_all_sqlyear_variants(
        self, mock_api, sqlyear, resolved_years, expected_year
    ):
        """Test de todas las variantes soportadas por --sqlyear en sql2doc."""
        mock_api.SAGE50year.return_value = resolved_years
        mock_api.build_query.return_value = f'SELECT * FROM "{expected_year}".dbo.clientes'
        proc = proceso(api=mock_api)
        proc.imprimir_diccionarios = MagicMock(return_value=True)

        result = proc.sql2doc("select * from #clientes", sqlyear=sqlyear, formato="txt")

        assert result is True
        mock_api.SAGE50year.assert_called_once_with(sqlyear, tyear=None)
        mock_api.build_query.assert_called_once_with(
            sql_template="select * from #clientes", sqlcomun=None, years=resolved_years
        )
        mock_api.sql_to_list.assert_called_once_with(
            query=f'SELECT * FROM "{expected_year}".dbo.clientes', as_dict=True
        )

    @patch("builtins.print")
    def test_sql2doc_rejects_non_select_queries(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        result = proc.sql2doc("DELETE FROM CLIENTES")

        assert result is False
        mock_api.build_query.assert_not_called()
        mock_api.sql_to_list.assert_not_called()
        mock_api.confsage50.logger.error.assert_called_once()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("No se exportan sentencias de escritura" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql2doc_rejects_multi_statement_queries(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        result = proc.sql2doc("SELECT 1; DROP TABLE CLIENTES")

        assert result is False
        mock_api.build_query.assert_not_called()
        mock_api.sql_to_list.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    @patch("builtins.print")
    def test_sql2doc_rejects_with_delete_queries(self, mock_print, mock_api):
        proc = proceso(api=mock_api)

        result = proc.sql2doc("WITH cte AS (SELECT * FROM CLIENTES) DELETE FROM cte")

        assert result is False
        mock_api.build_query.assert_not_called()
        mock_api.sql_to_list.assert_not_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Consulta no permitida" in call for call in print_calls)

    def test_sql2doc_applies_grupo_comunes_override(self, mock_api):
        mock_api.obtener_year_letra_nombre_comunes.return_value = (
            ["2024JX", "2025JX"],
            "JX",
            "Grupo 4",
        )
        mock_api.SAGE50year.return_value = ["2024JX", "2025JX"]
        mock_api.build_query.return_value = "SELECT * FROM union_clientes"
        proc = proceso(api=mock_api)
        proc.imprimir_diccionarios = MagicMock(return_value=True)

        result = proc.sql2doc("select * from #clientes", sqlyear="*", grupo_comunes="4")

        assert result is True
        mock_api.obtener_year_letra_nombre_comunes.assert_called_once_with("COMU0004")
        mock_api.SAGE50year.assert_called_once_with("*", tyear=["2024JX", "2025JX"])
        mock_api.build_query.assert_called_once_with(
            sql_template="select * from #clientes",
            sqlcomun="COMU0004",
            years=["2024JX", "2025JX"],
        )

    def test_sql2doc_groupby_wraps_union_query(self, mock_api):
        mock_api.SAGE50year.return_value = ["2017JX", "2018JX", "2019JX"]
        mock_api.build_query.return_value = (
            '(SELECT CODIGO, NOMBRE FROM "2017JX".dbo.clientes) UNION ALL '
            '(SELECT CODIGO, NOMBRE FROM "2018JX".dbo.clientes) UNION ALL '
            '(SELECT CODIGO, NOMBRE FROM "2019JX".dbo.clientes)'
        )
        proc = proceso(api=mock_api)
        proc.imprimir_diccionarios = MagicMock(return_value=True)

        result = proc.sql2doc(
            "select CODIGO, MAX(NOMBRE) from #clientes", sqlyear="@", groupby="CODIGO"
        )

        assert result is True
        mock_api.build_query.assert_called_once_with(
            sql_template="SELECT CODIGO, NOMBRE FROM #clientes",
            sqlcomun=None,
            years=["2017JX", "2018JX", "2019JX"],
        )
        exported_query = mock_api.sql_to_list.call_args.kwargs["query"]
        assert "GROUP BY CODIGO" in exported_query

    @patch("builtins.print")
    def test_sql_failure(self, mock_print, mock_api):
        """Test manejo de fallo en SQL"""
        mock_api.execute_query.side_effect = Exception("SQL Error")

        proc = proceso(api=mock_api)

        # Ejecutar
        proc.sql("SELECT * FROM TEST")

        # Verificar
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Fallo en sql" in call for call in print_calls)


class TestResetLog:
    """Tests para el método reset_log"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        return api

    def test_reset_log_executes_truncate_queries(self, mock_api):
        """Test que reset_log ejecuta queries de truncate"""
        proc = proceso(api=mock_api)

        # Ejecutar
        proc.reset_log()

        # Verificar que se llamó a execute_query dos veces
        assert mock_api.execute_query.call_count == 2

        # Verificar las queries
        calls = [str(call) for call in mock_api.execute_query.call_args_list]
        assert any("truncate table" in call for call in calls)
        assert any("log_analisis" in call for call in calls)
        assert any("log_error" in call for call in calls)


class TestLicencia:
    """Tests para el flujo de licencia y apertura de la pagina de ayuda."""

    _X11_OK = {"ok": True, "status": "valid", "data": {}, "demo": False}

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.lconecto = True
        api.confsage50 = MagicMock()
        return api

    @pytest.fixture(autouse=True)
    def _restore_x11_default(self):
        yield
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

    @patch("s50proceso._abrir_ayuda")
    @patch("builtins.print")
    def test_licencia_valida_no_abre_ayuda(self, mock_print, mock_abrir, mock_api):
        """Licencia valida (ok=True, no demo) no abre el navegador."""
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

        proceso(api=mock_api)

        mock_abrir.assert_not_called()

    @patch("s50proceso._abrir_ayuda")
    @patch("builtins.print")
    def test_licencia_demo_abre_ayuda(self, mock_print, mock_abrir, mock_api):
        """Licencia en demo (status=demo, sin key demo) abre el navegador."""
        mock_libwertyconfig.x11.return_value = {"ok": True, "status": "demo", "data": {}}

        proceso(api=mock_api)

        assert mock_abrir.called
        assert mock_abrir.call_args.args[0] == SAGE50BI_URL

    @patch("s50proceso._abrir_ayuda")
    @patch("builtins.print")
    def test_licencia_fallida_abre_ayuda(self, mock_print, mock_abrir, mock_api):
        """Licencia fallida (ok=False) abre el navegador."""
        mock_libwertyconfig.x11.return_value = {
            "ok": False,
            "status": "registration_failed",
            "data": None,
        }

        proceso(api=mock_api)

        assert mock_abrir.called
        assert mock_abrir.call_args.args[0] == SAGE50BI_URL

    @patch("builtins.print")
    @patch("s50proceso.datetime")
    def test_carencia_reciente_deshabilita_formulario(self, mock_dt, mock_print, mock_api):
        """Con menos de 7 dias no se fuerza el formulario de contacto."""
        from datetime import datetime, timedelta

        ahora = datetime(2026, 6, 25)
        mock_dt.now.return_value = ahora
        mock_dt.fromtimestamp.return_value = ahora - timedelta(days=3)
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

        proceso(api=mock_api)

        kwargs = mock_libwertyconfig.x11.call_args.kwargs
        assert kwargs["solicitar_datos_localhost"] is False
        assert kwargs["timeout_localhost"] == 30

    @patch("s50proceso._abrir_ayuda")
    @patch("builtins.print")
    @patch("s50proceso.datetime")
    def test_carencia_reciente_no_muestra_aviso_sage50bi(
        self, mock_dt, mock_print, mock_abrir, mock_api
    ):
        """El aviso SAGE50BI sigue la misma carencia que el formulario."""
        from datetime import datetime, timedelta

        ahora = datetime(2026, 6, 25)
        mock_dt.now.return_value = ahora
        mock_dt.fromtimestamp.return_value = ahora - timedelta(days=3)
        mock_libwertyconfig.x11.return_value = {"ok": True, "status": "demo", "data": {}}

        proceso(api=mock_api)

        mock_abrir.assert_not_called()

    @patch("builtins.print")
    @patch("s50proceso.datetime")
    def test_carencia_pasada_habilita_formulario(self, mock_dt, mock_print, mock_api):
        """Con 7 dias o mas se fuerza el formulario de contacto."""
        from datetime import datetime, timedelta

        ahora = datetime(2026, 6, 25)
        mock_dt.now.return_value = ahora
        mock_dt.fromtimestamp.return_value = ahora - timedelta(days=10)
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

        proceso(api=mock_api)

        kwargs = mock_libwertyconfig.x11.call_args.kwargs
        assert kwargs["solicitar_datos_localhost"] is True
        assert kwargs["timeout_localhost"] == 30

    @patch("builtins.print")
    def test_sin_config_ini_fuerza_datos(self, mock_print, mock_api, monkeypatch):
        """Sin config.ini (primera vez) se fuerza la solicitud de datos de contacto."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

        proceso(api=mock_api)

        kwargs = mock_libwertyconfig.x11.call_args.kwargs
        assert kwargs["solicitar_datos_localhost"] is True

    @patch("builtins.print")
    def test_evalua_licencia_antes_de_rechazar_sage50_desconectado(self, mock_print, mock_api):
        """Aunque SAGE50 no conecte, primero debe pasar por x11 para poder pedir datos."""
        mock_api.lconecto = False
        mock_libwertyconfig.x11.reset_mock()
        mock_libwertyconfig.x11.return_value = dict(self._X11_OK)

        proceso(api=mock_api)

        mock_libwertyconfig.x11.assert_called_once()
        mock_api.confsage50.logger.error.assert_called_once_with("No se pudo conectar con SAGE50")
