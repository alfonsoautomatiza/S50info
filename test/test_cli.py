import sys
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

# Create mocks before importing the app to avoid side effects
mock_libsage50 = MagicMock()
mock_proceso = MagicMock()
mock_libwertyupdate = MagicMock()
mock_libwertyconfig = MagicMock()

# Configure the API mock to simulate successful connection
mock_api_instance = MagicMock()
mock_api_instance.lconecto = True
mock_libsage50.apiSAGE50.return_value = mock_api_instance

# Patch sys.modules to provide our mocks
with patch.dict(sys.modules, {
    "libsage50": mock_libsage50,
    "proceso": mock_proceso,
    "libwertyupdate": mock_libwertyupdate,
    "libwertyconfig": mock_libwertyconfig,
}):
    # Import s50info after patching
    import s50info
    # Mock rich components to avoid rendering errors
    s50info.rprint = MagicMock(side_effect=print)
    s50info.console = MagicMock()
    s50info.Panel = MagicMock()

runner = CliRunner()

def setup_function():
    """Reset mocks before each test"""
    mock_libsage50.reset_mock()
    mock_proceso.reset_mock()
    mock_libwertyupdate.reset_mock()
    mock_api_instance.reset_mock()
    # Ensure connection stays True
    mock_api_instance.lconecto = True

    # Configure proceso mock
    mock_proceso_instance = MagicMock()
    mock_proceso.proceso.return_value = mock_proceso_instance


@patch("builtins.input", return_value="")
def test_sql_parameter(mock_input):
    """Test that --sql parameter correctly calls the processus sql method"""
    result = runner.invoke(s50info.app, ["--sql", "SELECT * FROM TEST"])

    assert result.exit_code == 0
    # Check if process was initialized
    mock_proceso.proceso.assert_called_once()
    # Check if sql method was called on the instance
    mock_proceso.proceso.return_value.sql.assert_called_once_with("SELECT * FROM TEST")

@patch("builtins.input", return_value="")
def test_sql2doc_parameters(mock_input):
    """Test --sql2doc with different format options"""
    result = runner.invoke(s50info.app, [
        "--sql2doc", "SELECT * FROM DATA",
        "--formato", "json",
        "--output", "results",
        "--comprimir"
    ])

    assert result.exit_code == 0
    mock_proceso.proceso.return_value.sqltodic.assert_called_once()

    # Verify arguments passed to sqltodic
    args, kwargs = mock_proceso.proceso.return_value.sqltodic.call_args
    assert args[0] == "SELECT * FROM DATA"
    assert kwargs["formato"] == "json"
    assert kwargs["nombre_archivo"] == "results"
    assert kwargs["comprimir"] is True

@patch("builtins.input", return_value="")
def test_clave_parameter(mock_input):
    """Test that --clave parameter passes correctly"""
    result = runner.invoke(s50info.app, ["--clave", "LICENSE_KEY"])

    assert result.exit_code == 0
    # Verify it reached the params object passed to proceso
    call_args = mock_proceso.proceso.call_args
    # First arg is 'para' (namespace)
    params = call_args[0][0]
    assert params.clave == "LICENSE_KEY"

@patch("builtins.input", return_value="")
def test_exec_script_parameter(mock_input, tmp_path):
    """Test --exe parameter to execute external script"""
    script_file = tmp_path / "myscript.py"
    script_file.write_text("print('running script')", encoding="utf-8")

    result = runner.invoke(s50info.app, ["--exe", str(script_file)])

    assert result.exit_code == 0
    assert "running script" in result.stdout

@patch("builtins.input", return_value="")
def test_noupdate_parameter(mock_input):
    """Test --noupdate parameter passes to update function"""
    result = runner.invoke(s50info.app, ["--sql", "SELECT 1", "--noupdate", "skip_reason"])

    assert result.exit_code == 0
    mock_libwertyupdate.update.assert_called_once()
    assert mock_libwertyupdate.update.call_args[1]["update"] == "skip_reason"

@patch("builtins.input", return_value="")
def test_api_connection_failure(mock_input):
    """Test graceful handling when API connection fails"""
    # Simulate failed connection
    mock_libsage50.apiSAGE50.return_value.lconecto = False

    result = runner.invoke(s50info.app, ["--sql", "SELECT 1"])

    assert result.exit_code == 0  # Should exit cleanly
    # Check that error message was printed (searching in stdout)
    assert "No se pudo conectar con SAGE50" in result.stdout
    # Process should NOT be initialized if connection failed
    mock_proceso.proceso.assert_not_called()
