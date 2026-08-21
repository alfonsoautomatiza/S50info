import importlib
import json
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _appdata_con_terminal_valido(tmp_path, monkeypatch):
    """Aísla APPDATA con un terminal SAGE50 válido para todos los tests de CLI."""
    appdata = tmp_path / "AppData" / "Roaming"
    terminal = tmp_path / "Sage50" / "Sage50Term"
    terminal.mkdir(parents=True)
    (terminal / "config.ini").touch()
    config_dir = appdata / "s50info"
    config_dir.mkdir(parents=True)
    (config_dir / "config.ini").write_text(f"[API]\nterminal = {terminal}\n", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(appdata))
    return appdata


def load_s50info_module(disable_usage_prompt=True):
    """Importa s50info con dependencias externas mockeadas.

    Restaura `sys.modules` tras el import para no contaminar a otros
    módulos de test (p. ej. los `@patch("s50proceso.*")` de test_proceso).
    """
    fake_pysage50e = ModuleType("pysage50e")
    fake_sage_debug_config = ModuleType("pysage50e.sage_debug_config")
    fake_proceso_module = MagicMock()

    mock_api_instance = MagicMock()
    mock_api_instance.lconecto = True
    fake_pysage50e.apiSAGE50 = MagicMock(return_value=mock_api_instance)
    fake_sage_debug_config.configure_debug_logging = MagicMock(return_value=False)
    fake_sage_debug_config.is_debug_enabled = MagicMock(return_value=False)

    mock_proceso_instance = MagicMock()
    fake_proceso_module.proceso.return_value = mock_proceso_instance

    mocked = {
        "s50info": sys.modules.pop("s50info", None),
        "polars": sys.modules.pop("polars", None),
        "pysage50e": sys.modules.get("pysage50e"),
        "pysage50e.sage_debug_config": sys.modules.get("pysage50e.sage_debug_config"),
        "s50proceso": sys.modules.get("s50proceso"),
        "s50onboarding": sys.modules.get("s50onboarding"),
        "s50store": sys.modules.get("s50store"),
    }
    sys.modules["pysage50e"] = fake_pysage50e
    sys.modules["pysage50e.sage_debug_config"] = fake_sage_debug_config
    sys.modules["s50proceso"] = fake_proceso_module
    sys.modules["s50onboarding"] = MagicMock()
    sys.modules["s50store"] = MagicMock()
    try:
        module = importlib.import_module("s50info")
    finally:
        for name, original in mocked.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    module.rprint = MagicMock(side_effect=print)
    module.s50onboarding.mostrar_if_necesario = MagicMock()
    module.s50store.puerta_update_obligatorio = MagicMock(return_value=False)
    module.Panel = MagicMock()
    module._pausa_final = MagicMock()
    if disable_usage_prompt:
        module._record_successful_use_and_maybe_show_cta = MagicMock()

    return module, fake_pysage50e, fake_proceso_module, mock_api_instance


def test_import_does_not_import_polars():
    load_s50info_module()

    assert "polars" not in sys.modules


def test_default_flow_calls_info_command():
    module, _, mock_proceso_module, _ = load_s50info_module()

    result = runner.invoke(module.app, [])

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.info.assert_called_once_with(
        pausa=True, grupo_comunes=None
    )


def test_first_launch_without_terminal_runs_wizard_and_exits_clean(monkeypatch):
    module, fake_pysage50e, mock_proceso_module, _ = load_s50info_module()
    config_path = module._app_state_dir() / module.CONFIG_FILE
    config_path.write_text("", encoding="utf-8")

    llamado = []
    monkeypatch.setattr(
        module.s50setup, "asistente_terminal", lambda cp: llamado.append(cp) or None
    )

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 0
    assert llamado == [config_path]
    fake_pysage50e.apiSAGE50.assert_not_called()
    mock_proceso_module.proceso.assert_not_called()
    assert "Vuelve a ejecutar s50info" in result.stdout


def test_first_launch_wizard_saves_terminal_and_connects(tmp_path, monkeypatch):
    module, fake_pysage50e, mock_proceso_module, mock_api_instance = load_s50info_module()
    config_path = module._app_state_dir() / module.CONFIG_FILE
    config_path.write_text("", encoding="utf-8")
    terminal = tmp_path / "NuevoTerm"
    terminal.mkdir()
    (terminal / "config.ini").touch()

    def fake_asistente(cp):
        module.s50setup.guardar_terminal(cp, terminal)
        return terminal

    monkeypatch.setattr(module.s50setup, "asistente_terminal", fake_asistente)

    result = runner.invoke(module.app, [])

    assert result.exit_code == 0
    assert config_path.is_file()
    assert "terminal" in config_path.read_text(encoding="utf-8")
    fake_pysage50e.apiSAGE50.assert_called_once_with(dirconfig=str(config_path.parent))
    mock_proceso_module.proceso.assert_called_once_with(
        api=mock_api_instance,
        config_path=config_path,
        directorio_resultados=str(module._cwd_original / "resultados"),
    )


def test_info_command_allows_grupo_comunes_override():
    module, _, mock_proceso_module, _ = load_s50info_module()

    result = runner.invoke(module.app, ["info", "--grupo-comunes", "4"])

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.info.assert_called_once_with(
        pausa=True, grupo_comunes="4"
    )


def test_sql_command_forwards_sqlyear_and_grupo_comunes():
    module, _, mock_proceso_module, _ = load_s50info_module()
    mock_proceso_module.proceso.return_value.sql.return_value = True

    result = runner.invoke(
        module.app,
        [
            "sql",
            "SELECT * FROM TEST",
            "--sqlyear",
            "2025JX",
            "--grupo-comunes",
            "7",
            "--groupby",
            "CODIGO",
        ],
    )

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.sql.assert_called_once_with(
        "SELECT * FROM TEST",
        sqlyear="2025JX",
        grupo_comunes="7",
        groupby="CODIGO",
        sage50=False,
    )
    module._record_successful_use_and_maybe_show_cta.assert_called_once_with()


def test_sql_command_does_not_record_usage_on_failure():
    module, _, mock_proceso_module, _ = load_s50info_module()
    mock_proceso_module.proceso.return_value.sql.return_value = False

    result = runner.invoke(module.app, ["sql", "DELETE FROM TEST"])

    assert result.exit_code == 0
    module._record_successful_use_and_maybe_show_cta.assert_not_called()


def test_export_command_forwards_all_arguments():
    module, _, mock_proceso_module, _ = load_s50info_module()
    mock_proceso_module.proceso.return_value.sql2doc.return_value = True

    result = runner.invoke(
        module.app,
        [
            "export",
            "SELECT * FROM DATA",
            "--sqlyear",
            "2024JX,2025JX",
            "--grupo-comunes",
            "COMU0004",
            "--formato",
            "json",
            "--output",
            "results",
            "--zip",
        ],
    )

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.sql2doc.assert_called_once_with(
        "SELECT * FROM DATA",
        sqlyear="2024JX,2025JX",
        grupo_comunes="COMU0004",
        groupby=None,
        sage50=False,
        formato="json",
        nombre_archivo="results",
        plantilla=None,
        comprimir=True,
    )
    module._record_successful_use_and_maybe_show_cta.assert_called_once_with()


def test_export_command_does_not_record_usage_on_failure():
    module, _, mock_proceso_module, _ = load_s50info_module()
    mock_proceso_module.proceso.return_value.sql2doc.return_value = False

    result = runner.invoke(module.app, ["export", "DELETE FROM DATA"])

    assert result.exit_code == 0
    module._record_successful_use_and_maybe_show_cta.assert_not_called()


def test_run_command_executes_python_file(tmp_path):
    module, _, _, _ = load_s50info_module()
    script_file = tmp_path / "myscript.py"
    script_file.write_text("print('running script')", encoding="utf-8")

    result = runner.invoke(module.app, ["run", str(script_file)])

    assert result.exit_code == 0
    assert "running script" in result.stdout
    module._record_successful_use_and_maybe_show_cta.assert_called_once_with()


def test_run_command_directory_does_not_record_usage_when_script_fails(tmp_path):
    module, _, _, _ = load_s50info_module()
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "first.py").write_text("print('first script')", encoding="utf-8")
    (script_dir / "second.py").write_text("raise RuntimeError('boom')", encoding="utf-8")

    result = runner.invoke(module.app, ["run", str(script_dir)])

    assert result.exit_code == 1
    assert "first script" in result.stdout
    assert "boom" in result.stdout
    module._record_successful_use_and_maybe_show_cta.assert_not_called()


def test_run_command_skip_polars_cpu_check_sets_env_before_runpy(tmp_path, monkeypatch):
    module, _, _, _ = load_s50info_module()
    script_file = tmp_path / "myscript.py"
    script_file.write_text("print('running script')", encoding="utf-8")
    monkeypatch.delenv("POLARS_SKIP_CPU_CHECK", raising=False)

    def assert_env_before_runpy(*args, **kwargs):
        assert os.environ["POLARS_SKIP_CPU_CHECK"] == "1"

    monkeypatch.setattr(module.runpy, "run_path", assert_env_before_runpy)

    result = runner.invoke(module.app, ["run", "--skip-polars-cpu-check", str(script_file)])

    assert result.exit_code == 0
    assert os.environ["POLARS_SKIP_CPU_CHECK"] == "1"


def test_run_command_polars_alias_sets_cpu_check_env(tmp_path, monkeypatch):
    module, _, _, _ = load_s50info_module()
    script_file = tmp_path / "myscript.py"
    script_file.write_text("print('running script')", encoding="utf-8")
    monkeypatch.delenv("POLARS_SKIP_CPU_CHECK", raising=False)
    monkeypatch.setattr(module.runpy, "run_path", MagicMock())

    result = runner.invoke(module.app, ["run", "--polars-skip-cpu-check", str(script_file)])

    assert result.exit_code == 0
    assert os.environ["POLARS_SKIP_CPU_CHECK"] == "1"


def test_run_command_uses_script_folder_by_default(tmp_path):
    module, _, _, _ = load_s50info_module()
    state_dir = tmp_path / "AppData" / "Roaming" / "s50info"
    script_dir = state_dir / "script"
    script_dir.mkdir(parents=True)
    (script_dir / "auto.py").write_text("print('auto script')", encoding="utf-8")

    result = runner.invoke(module.app, ["run"])

    assert result.exit_code == 0
    assert "auto script" in result.stdout


def test_run_command_recommends_script_folder_when_missing(tmp_path, monkeypatch):
    module, _, _, _ = load_s50info_module()
    monkeypatch.setattr(module, "_directorio_ejecutable", lambda: tmp_path)

    result = runner.invoke(module.app, ["run"])

    assert result.exit_code == 1
    assert "Recomendación:" in result.stdout
    assert "script" in result.stdout


def test_app_uses_app_state_dir_as_working_directory(tmp_path):
    module, _, _, _ = load_s50info_module()

    result = runner.invoke(module.app, [])

    assert result.exit_code == 0
    assert os.getcwd() == str(module._app_state_dir())


def test_output_shows_working_folder_location(tmp_path):
    module, _, _, _ = load_s50info_module()

    result = runner.invoke(module.app, ["info"])

    assert result.exit_code == 0
    assert f"Directorio Config.ini: {module._app_state_dir()}" in result.stdout


def test_proceso_uses_original_cwd_for_resultados(tmp_path, monkeypatch):
    module, _, fake_proceso_module, _ = load_s50info_module()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(module.app, ["info"])

    assert result.exit_code == 0
    _, kwargs = fake_proceso_module.proceso.call_args
    assert kwargs["directorio_resultados"] == str(tmp_path / "resultados")


def test_script_folder_is_regenerated_in_working_dir_when_missing(tmp_path, monkeypatch):
    module, _, _, _ = load_s50info_module()
    state_dir = tmp_path / "AppData" / "Roaming" / "s50info"
    origen = tmp_path / "script"
    origen.mkdir(parents=True)
    (origen / "plantilla.py").write_text("print('regenerada')", encoding="utf-8")
    monkeypatch.setattr(module, "_directorio_ejecutable", lambda: tmp_path)

    module._inicializar_directorio_trabajo()

    assert os.getcwd() == str(state_dir)
    assert (state_dir / "script" / "plantilla.py").is_file()


def test_usage_prompt_shows_at_first_threshold(tmp_path, capsys):
    module, _, _, _ = load_s50info_module(disable_usage_prompt=False)
    state_path = tmp_path / "usage_prompt.json"

    for _ in range(module.USAGE_PROMPT_FIRST_USE - 1):
        module._record_successful_use_and_maybe_show_cta(state_path)

    assert "utm_campaign=s50info_contact" not in capsys.readouterr().out

    module._record_successful_use_and_maybe_show_cta(state_path)

    output = capsys.readouterr().out
    assert "Contactanos" in output
    assert "utm_source=cli" in output
    assert "utm_medium=post_command" in output
    assert "utm_campaign=s50info_contact" in output


def test_usage_prompt_does_not_repeat_until_interval(tmp_path, capsys):
    module, _, _, _ = load_s50info_module(disable_usage_prompt=False)
    state_path = tmp_path / "usage_prompt.json"
    state_path.write_text(
        json.dumps(
            {
                "successful_uses": module.USAGE_PROMPT_FIRST_USE,
                "last_prompt_successful_uses": module.USAGE_PROMPT_FIRST_USE,
            }
        ),
        encoding="utf-8",
    )

    for _ in range(module.USAGE_PROMPT_INTERVAL - 1):
        module._record_successful_use_and_maybe_show_cta(state_path)

    assert "utm_campaign=s50info_contact" not in capsys.readouterr().out

    module._record_successful_use_and_maybe_show_cta(state_path)

    assert "utm_campaign=s50info_contact" in capsys.readouterr().out


def test_usage_prompt_state_failure_does_not_break_output(monkeypatch, capsys):
    module, _, _, _ = load_s50info_module(disable_usage_prompt=False)

    def fail_write(*args, **kwargs):
        raise OSError("read-only state")

    monkeypatch.setattr(module.Path, "write_text", fail_write)

    module._record_successful_use_and_maybe_show_cta(module.Path("/state/usage_prompt.json"))

    assert capsys.readouterr().out == ""


def test_reset_command_calls_reset_log():
    module, _, mock_proceso_module, _ = load_s50info_module()

    result = runner.invoke(module.app, ["reset"])

    assert result.exit_code == 0
    mock_proceso_module.proceso.return_value.reset_log.assert_called_once_with()


def test_version_flag_shows_program_version():
    module, _, mock_proceso_module, _ = load_s50info_module()

    result = runner.invoke(module.app, ["--v"])

    assert result.exit_code == 0
    assert f"s50info v{module.S50INFO_VERSION}" in result.stdout
    assert "lista de comandos" in result.stdout
    mock_proceso_module.proceso.assert_not_called()


def test_version_command_and_short_flag_show_version():
    module, _, _, _ = load_s50info_module()

    for argv in (["version"], ["-v"]):
        result = runner.invoke(module.app, argv)

        assert result.exit_code == 0
        assert f"s50info v{module.S50INFO_VERSION}" in result.stdout
        assert "lista de comandos" in result.stdout


def test_manual_flag_opens_license_manual(monkeypatch):
    module, _, mock_proceso_module, _ = load_s50info_module()
    abrir = MagicMock()
    monkeypatch.setattr(module, "_abrir_manual", abrir)

    result = runner.invoke(module.app, ["--m"])

    assert result.exit_code == 0
    abrir.assert_called_once_with()
    assert module.MANUAL_URL in result.stdout
    assert "lista de comandos" in result.stdout
    mock_proceso_module.proceso.assert_not_called()


def test_manual_command_opens_license_manual(monkeypatch):
    module, _, _, _ = load_s50info_module()
    abrir = MagicMock()
    monkeypatch.setattr(module, "_abrir_manual", abrir)

    result = runner.invoke(module.app, ["manual"])

    assert result.exit_code == 0
    abrir.assert_called_once_with()
    assert module.MANUAL_URL in result.stdout


def _panel_passthrough(*args, **kwargs):
    return " ".join(str(a) for a in args)


def test_default_flow_reminds_sage50bi_and_help(monkeypatch):
    module, _, _, _ = load_s50info_module()
    monkeypatch.setattr(module, "Panel", _panel_passthrough)

    result = runner.invoke(module.app, [])

    assert result.exit_code == 0
    assert "Sage50BI" in result.stdout
    assert "otro producto" in result.stdout
    assert module.SAGE50BI_URL in result.stdout
    assert "lista de comandos" in result.stdout


def test_info_command_reminds_help(monkeypatch):
    module, _, _, _ = load_s50info_module()
    monkeypatch.setattr(module, "Panel", _panel_passthrough)

    result = runner.invoke(module.app, ["info"])

    assert result.exit_code == 0
    assert "Sage50BI" in result.stdout
    assert "otro producto" in result.stdout
    assert "lista de comandos" in result.stdout


def test_unknown_command_shows_reminder_and_help_hint(monkeypatch, capsys):
    module, _, _, _ = load_s50info_module()
    monkeypatch.setattr(sys, "argv", ["s50info", "comando_inexistente"])

    with pytest.raises(SystemExit) as exc_info:
        module._cli_main()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "No such command" in captured.err
    # En un error de uso no se promociona Sage50BI: solo el hint de ayuda.
    assert "lista de comandos" in captured.out
    assert "Sage50BI" not in captured.out


def test_invalid_option_shows_reminder_and_help_hint(monkeypatch, capsys):
    module, _, _, _ = load_s50info_module()
    monkeypatch.setattr(sys, "argv", ["s50info", "sql", "--flag_inexistente"])

    with pytest.raises(SystemExit) as exc_info:
        module._cli_main()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "lista de comandos" in captured.out


def test_store_update_gate_blocks_before_subcommand():
    module, _, mock_proceso_module, _ = load_s50info_module()
    puerta = MagicMock(return_value=True)
    module.s50store.puerta_update_obligatorio = puerta

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 1
    puerta.assert_called_once_with(
        nombre_app="s50info", store_product_id=module.STORE_PRODUCT_ID
    )
    mock_proceso_module.proceso.assert_not_called()


def test_store_update_gate_passes_when_no_update():
    module, _, mock_proceso_module, _ = load_s50info_module()

    result = runner.invoke(module.app, ["info"])

    assert result.exit_code == 0
    module.s50store.puerta_update_obligatorio.assert_called_once()
    mock_proceso_module.proceso.return_value.info.assert_called_once()


def test_missing_sage_terminal_has_product_facing_message(tmp_path):
    module, fake_pysage50e, _, mock_api_instance = load_s50info_module()
    mock_api_instance.lconecto = False
    mock_api_instance.confsage50.cvariables = {
        "api#terminal": str(tmp_path / "missing-sage-terminal")
    }
    fake_pysage50e.apiSAGE50.return_value = mock_api_instance

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 0
    assert "Terminal de Sage 50 no encontrado." in result.stdout
    assert "config.ini" not in result.stdout


def test_unexpected_api_error_keeps_technical_message():
    module, fake_pysage50e, _, _ = load_s50info_module()
    fake_pysage50e.apiSAGE50.side_effect = RuntimeError("database unavailable")

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 0
    assert "database unavailable" in result.stdout
    assert "Terminal de Sage 50 no encontrado." not in result.stdout


def test_api_connection_failure_exits_cleanly(tmp_path):
    module, fake_pysage50e, mock_proceso_module, mock_api_instance = load_s50info_module()
    terminal_path = tmp_path / "Sage50Term"
    terminal_path.mkdir()
    (terminal_path / "config.ini").touch()
    mock_api_instance.lconecto = False
    mock_api_instance.confsage50.cvariables = {"api#terminal": str(terminal_path)}
    fake_pysage50e.apiSAGE50.return_value = mock_api_instance

    result = runner.invoke(module.app, ["sql", "SELECT 1"])

    assert result.exit_code == 0
    assert "No se pudo conectar con SAGE50" in result.stdout
    config_path = module._app_state_dir() / module.CONFIG_FILE
    mock_proceso_module.proceso.assert_called_once_with(
        api=mock_api_instance,
        config_path=config_path,
        directorio_resultados=str(module._cwd_original / "resultados"),
    )
