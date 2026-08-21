"""Tests de s50store: puerta de actualización obligatoria de Microsoft Store."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import s50store  # noqa: E402


def _resultado(returncode=0, stdout=""):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    return r


# --- detección de identidad de paquete --------------------------------


def test_package_family_name_none_fuera_de_win32(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert s50store.package_family_name() is None


# --- consulta a la store (parseo fail-open) ----------------------------


def test_actualizacion_disponible_parsea_true_y_false(monkeypatch):
    llamada = MagicMock(side_effect=[_resultado(0, "True\n"), _resultado(0, "False")])
    monkeypatch.setattr(s50store.subprocess, "run", llamada)

    assert s50store.actualizacion_disponible("App.Test_abc") is True
    assert s50store.actualizacion_disponible("App.Test_abc") is False


@pytest.mark.parametrize(
    "rc,salida",
    [(1, "True"), (0, "Timeout"), (0, "Error"), (0, ""), (0, "otra cosa")],
)
def test_actualizacion_disponible_fail_open(rc, salida, monkeypatch):
    monkeypatch.setattr(
        s50store.subprocess, "run", MagicMock(return_value=_resultado(rc, salida))
    )

    assert s50store.actualizacion_disponible("App.Test_abc") is None


def test_actualizacion_disponible_timeout_de_subproceso(monkeypatch):
    monkeypatch.setattr(
        s50store.subprocess,
        "run",
        MagicMock(side_effect=subprocess.TimeoutExpired(cmd="ps", timeout=25)),
    )

    assert s50store.actualizacion_disponible("App.Test_abc") is None


def test_actualizacion_disponible_rechaza_family_con_caracteres_raros(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(s50store.subprocess, "run", run)

    assert s50store.actualizacion_disponible("App.Test; rm -rf") is None
    run.assert_not_called()


# --- puerta de bloqueo -------------------------------------------------


def test_puerta_sin_paquete_no_consulta_ni_bloquea(monkeypatch):
    consultar = MagicMock()
    monkeypatch.setattr(s50store, "package_family_name", MagicMock(return_value=None))
    monkeypatch.setattr(s50store, "actualizacion_disponible", consultar)

    assert s50store.puerta_update_obligatorio() is False
    consultar.assert_not_called()


def test_puerta_con_update_disponible_bloquea_y_abre_tienda(monkeypatch, capsys):
    monkeypatch.setattr(
        s50store, "package_family_name", MagicMock(return_value="InfoMSD.s50info_x")
    )
    monkeypatch.setattr(
        s50store, "actualizacion_disponible", MagicMock(return_value=True)
    )
    abrir = MagicMock()
    monkeypatch.setattr(s50store, "abrir_tienda", abrir)

    assert s50store.puerta_update_obligatorio(nombre_app="s50info") is True
    abrir.assert_called_once()
    salida = capsys.readouterr().out
    assert "obligatoria" in salida
    assert "s50info" in salida


def test_puerta_fail_open_none_y_false_dejan_pasar(monkeypatch, capsys):
    monkeypatch.setattr(
        s50store, "package_family_name", MagicMock(return_value="InfoMSD.s50info_x")
    )
    abrir = MagicMock()
    monkeypatch.setattr(s50store, "abrir_tienda", abrir)

    for respuesta in (None, False):
        monkeypatch.setattr(
            s50store, "actualizacion_disponible", MagicMock(return_value=respuesta)
        )
        assert s50store.puerta_update_obligatorio() is False
        abrir.assert_not_called()

    assert capsys.readouterr().out == ""
