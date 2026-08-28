import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Asegurar que pytest encuentra las librerías compartidas.
sys.path.insert(0, "/home/alfonso/py/mislibrerias")

import wertyfeedback


@pytest.fixture(autouse=True)
def _restore_sys_modules(monkeypatch):
    """Limpia los módulos cacheados antes de cada test para aislar imports."""
    monkeypatch.delitem(sys.modules, "wertyfeedback", raising=False)
    monkeypatch.delitem(sys.modules, "libwertyemail", raising=False)
    monkeypatch.delitem(sys.modules, "libwertylog", raising=False)


def test_resilient_import_adds_fallback_path(monkeypatch):
    """Si libwertyemail no está en PYTHONPATH, se añade la ruta de mislibrerias."""
    # Asegurar que el módulo no está cacheado y que la ruta real no está aún.
    fallback = "/home/alfonso/py/mislibrerias"
    monkeypatch.delitem(sys.modules, "wertyfeedback", raising=False)
    monkeypatch.delitem(sys.modules, "libwertyemail", raising=False)
    monkeypatch.delitem(sys.modules, "libwertylog", raising=False)
    if fallback in sys.path:
        sys.path.remove(fallback)

    import wertyfeedback as wf

    assert fallback in sys.path
    assert wf.AVAILABLE is True
    assert wf.ErrorFeedback is not None


def test_get_feedback_returns_none_when_lib_unavailable(monkeypatch):
    """Si la librería no está disponible, get_feedback devuelve None."""
    monkeypatch.setitem(sys.modules, "libwertyemail", None)

    import wertyfeedback as wf

    assert wf.AVAILABLE is False
    assert wf.get_feedback("test", Path("/tmp/test")) is None


def test_console_ask_permission_true_when_user_accepts(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "s")

    assert wertyfeedback.console_ask_permission("¿Enviar") is True


def test_console_ask_permission_true_with_yes(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "SI")

    assert wertyfeedback.console_ask_permission("¿Enviar") is True


def test_console_ask_permission_false_when_user_rejects(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    assert wertyfeedback.console_ask_permission("¿Enviar") is False


def test_console_ask_permission_false_when_not_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert wertyfeedback.console_ask_permission("¿Enviar") is False


def test_console_ask_permission_false_on_eof(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError()))

    assert wertyfeedback.console_ask_permission("¿Enviar") is False


def test_console_ask_permission_false_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(
        "builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
    )

    assert wertyfeedback.console_ask_permission("¿Enviar") is False


def test_send_on_error_logs_and_sends_when_user_accepts(monkeypatch):
    feedback = MagicMock()
    context = MagicMock()
    feedback.error.return_value = context
    feedback.ask_and_send_log.return_value = True
    exc = ValueError("boom")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "s")

    result = wertyfeedback.send_on_error(feedback, exc)

    assert result is True
    feedback.error.assert_called_once()
    feedback.ask_and_send_log.assert_called_once()
    call_kwargs = feedback.ask_and_send_log.call_args.kwargs
    assert call_kwargs["context"] is context
    assert "ask_permission_callback" in call_kwargs


def test_send_on_error_returns_false_when_not_interactive(monkeypatch):
    feedback = MagicMock()
    exc = ValueError("boom")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    result = wertyfeedback.send_on_error(feedback, exc)

    assert result is False
    feedback.error.assert_called_once()
    feedback.ask_and_send_log.assert_not_called()


def test_send_on_error_returns_false_when_feedback_is_none():
    assert wertyfeedback.send_on_error(None, ValueError("boom")) is False


def test_send_on_error_uses_custom_message(monkeypatch):
    feedback = MagicMock()
    feedback.error.return_value = None
    exc = ValueError("boom")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    wertyfeedback.send_on_error(feedback, exc, message="Error personalizado")

    feedback.error.assert_called_once_with("Error personalizado", exc=exc)


def test_feedback_collector_creation_and_last_error():
    collector = wertyfeedback.FeedbackCollector(
        app_name="testapp",
        state_dir=Path("/tmp/testapp"),
        support_email="soporte@test.com",
    )

    assert collector.app_name == "testapp"
    assert collector.log_dir == Path("/tmp/testapp/logs")
    assert collector.log_file == "testapp.log"
    assert collector.support_email == "soporte@test.com"
    assert collector.last_error is None or collector._feedback is not None


def test_feedback_collector_error_delegates_to_error_feedback(monkeypatch):
    mock_ef = MagicMock()
    mock_context = MagicMock()
    mock_ef.return_value.error.return_value = mock_context
    mock_ef.return_value.last_error = mock_context
    monkeypatch.setattr(wertyfeedback, "ErrorFeedback", mock_ef)
    monkeypatch.setattr(wertyfeedback, "AVAILABLE", True)

    collector = wertyfeedback.FeedbackCollector(
        app_name="testapp",
        state_dir=Path("/tmp/testapp"),
        support_email="soporte@test.com",
    )
    exc = ValueError("fallo")
    context = collector.error("Error de prueba", exc=exc)

    assert context is mock_context
    mock_ef.return_value.error.assert_called_once_with(
        "Error de prueba", exc=exc, send_email=False
    )
    assert collector.last_error is mock_context


def test_feedback_collector_ask_and_send_log_without_email_returns_false():
    collector = wertyfeedback.FeedbackCollector(
        app_name="testapp",
        state_dir=Path("/tmp/testapp"),
        support_email="",
    )

    assert collector.ask_and_send_log() is False
