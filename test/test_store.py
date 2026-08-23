"""Tests de s50store: puerta de actualización obligatoria vía DisplayCatalog."""

import subprocess
import sys
import urllib.error
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


def _respuesta_http(payload: bytes):
    fake = MagicMock()
    fake.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=payload)))
    fake.__exit__ = MagicMock(return_value=False)
    return fake


def _payload_catalogo(*full_names: str) -> bytes:
    packages = [{"PackageFullName": fn} for fn in full_names]
    import json

    return json.dumps(
        {"Products": [{"DisplaySkuAvailabilities": [{"Sku": {"Properties": {"Packages": packages}}}]}]}
    ).encode()


# --- detección de identidad de paquete ---------------------------------


def test_package_full_name_none_fuera_de_win32(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert s50store.package_full_name() is None


# --- parseo de versiones ------------------------------------------------


def test_version_de_full_name_parsea_version_real():
    fn = "InfoMSD.s50info_2.2.1.0_neutral__xjc995t8xskrw"

    assert s50store.version_de_full_name(fn) == (2, 2, 1, 0)


@pytest.mark.parametrize("basura", ["", "sin version", "app__hash"])
def test_version_de_full_name_rechaza_basura(basura):
    assert s50store.version_de_full_name(basura) is None


def test_family_de_full_name_deriva_family_correcto():
    fn = "InfoMSD.s50info_2.2.1.0_neutral__xjc995t8xskrw"

    assert s50store.family_de_full_name(fn) == "InfoMSD.s50info_xjc995t8xskrw"


@pytest.mark.parametrize("basura", ["", "sin hash", "solo_nombre_"])
def test_family_de_full_name_rechaza_basura(basura):
    assert s50store.family_de_full_name(basura) == ""


# --- consulta a DisplayCatalog -----------------------------------------


def test_version_tienda_extrae_version_del_catalogo(monkeypatch):
    urlopen = MagicMock(
        return_value=_respuesta_http(_payload_catalogo("InfoMSD.s50info_2.2.1.0_neutral__xjc995t8xskrw"))
    )
    monkeypatch.setattr(s50store.urlrequest, "urlopen", urlopen)

    assert s50store.version_tienda("9N8P7XNX68X3") == (2, 2, 1, 0)
    assert "9N8P7XNX68X3" in urlopen.call_args[0][0].full_url


def test_version_tienda_queda_con_la_mayor(monkeypatch):
    urlopen = MagicMock(
        return_value=_respuesta_http(
            _payload_catalogo(
                "InfoMSD.s50info_2.2.1.0_x64__xjc995t8xskrw",
                "InfoMSD.s50info_2.3.0.0_neutral__xjc995t8xskrw",
            )
        )
    )
    monkeypatch.setattr(s50store.urlrequest, "urlopen", urlopen)

    assert s50store.version_tienda("9N8P7XNX68X3") == (2, 3, 0, 0)


@pytest.mark.parametrize(
    "excepcion",
    [
        urllib.error.URLError("sin red"),
        TimeoutError(),
        ValueError("json roto"),
    ],
)
def test_version_tienda_fail_open_ante_errores(excepcion, monkeypatch):
    if isinstance(excepcion, ValueError):
        urlopen = MagicMock(return_value=_respuesta_http(b"{no soy json"))
    else:
        urlopen = MagicMock(side_effect=excepcion)
    monkeypatch.setattr(s50store.urlrequest, "urlopen", urlopen)

    assert s50store.version_tienda("9N8P7XNX68X3") is None


def test_version_tienda_sin_productos_devuelve_none(monkeypatch):
    import json

    urlopen = MagicMock(return_value=_respuesta_http(json.dumps({"Products": []}).encode()))
    monkeypatch.setattr(s50store.urlrequest, "urlopen", urlopen)

    assert s50store.version_tienda("9N0000000000") is None


# --- instalación silenciosa ---------------------------------------------


def test_disparar_silenciosa_parsea_estados(monkeypatch):
    run = MagicMock(side_effect=[_resultado(0, "COMPLETADA\n"), _resultado(0, "EN_CURSO")])
    monkeypatch.setattr(s50store.subprocess, "run", run)

    assert s50store.disparar_actualizacion_silenciosa("App.X_abc") == "completada"
    assert s50store.disparar_actualizacion_silenciosa("App.X_abc") == "en_curso"


def test_disparar_sin_update_rolldout_se_diferencia(monkeypatch):
    monkeypatch.setattr(
        s50store.subprocess,
        "run",
        MagicMock(return_value=_resultado(0, "SIN_UPDATE")),
    )

    assert s50store.disparar_actualizacion_silenciosa("App.X_abc") == "sin_update"


@pytest.mark.parametrize("salida", ["Timeout", "Error", "ERROR_ESTADO", "", "otra"])
def test_disparar_sin_update_o_fallo_devuelve_none(salida, monkeypatch):
    monkeypatch.setattr(
        s50store.subprocess, "run", MagicMock(return_value=_resultado(0, salida))
    )

    assert s50store.disparar_actualizacion_silenciosa("App.X_abc") is None


def test_disparar_rechaza_family_invalido(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(s50store.subprocess, "run", run)

    assert s50store.disparar_actualizacion_silenciosa("App; rm") is None
    run.assert_not_called()


def test_disparar_timeout_de_subproceso(monkeypatch):
    monkeypatch.setattr(
        s50store.subprocess,
        "run",
        MagicMock(side_effect=subprocess.TimeoutExpired(cmd="ps", timeout=120)),
    )

    assert s50store.disparar_actualizacion_silenciosa("App.X_abc") is None


# --- puerta de bloqueo --------------------------------------------------


def _instalar_escenario(monkeypatch, instalada, tienda, silenciosa=None):
    monkeypatch.setattr(s50store, "package_full_name", MagicMock(return_value="InfoMSD.s50info_2.2.1.0_neutral__x"))
    monkeypatch.setattr(s50store, "version_de_full_name", MagicMock(return_value=instalada))
    monkeypatch.setattr(s50store, "version_tienda", MagicMock(return_value=tienda))
    abrir = MagicMock()
    monkeypatch.setattr(s50store, "abrir_tienda", abrir)
    disparar = MagicMock(return_value=silenciosa)
    monkeypatch.setattr(s50store, "disparar_actualizacion_silenciosa", disparar)
    return abrir, disparar


def test_puerta_silenciosa_completada_continua_ya_actualizado(monkeypatch, capsys):
    abrir, _ = _instalar_escenario(
        monkeypatch, (2, 2, 1, 0), (2, 3, 0, 0), silenciosa="completada"
    )

    assert (
        s50store.puerta_update_obligatorio(nombre_app="s50info", store_product_id="9NX")
        is False
    )
    abrir.assert_not_called()
    salida = capsys.readouterr().out
    assert "actualizado" in salida and "s50info" in salida


def test_puerta_silenciosa_en_curso_bloquea_sin_abrir_tienda(monkeypatch, capsys):
    abrir, _ = _instalar_escenario(
        monkeypatch, (2, 2, 1, 0), (2, 3, 0, 0), silenciosa="en_curso"
    )

    assert (
        s50store.puerta_update_obligatorio(nombre_app="s50info", store_product_id="9NX")
        is True
    )
    abrir.assert_not_called()
    salida = capsys.readouterr().out
    assert "vuelve a ejecutar" in salida


def test_puerta_fallback_abre_tienda_si_silenciosa_falla(monkeypatch, capsys):
    abrir, _ = _instalar_escenario(
        monkeypatch, (2, 2, 1, 0), (2, 3, 0, 0), silenciosa=None
    )

    assert (
        s50store.puerta_update_obligatorio(nombre_app="s50info", store_product_id="9NX")
        is True
    )
    abrir.assert_called_once()
    assert "obligatoria" in capsys.readouterr().out


def test_puerta_rollout_sin_update_en_tienda_deja_pasar(monkeypatch, capsys):
    # DisplayCatalog dice que hay versión nueva pero la Store aún no la sirve
    abrir, _ = _instalar_escenario(
        monkeypatch, (2, 2, 1, 0), (2, 3, 0, 0), silenciosa="sin_update"
    )

    assert (
        s50store.puerta_update_obligatorio(nombre_app="s50info", store_product_id="9NX")
        is False
    )
    abrir.assert_not_called()
    assert "todavía no está disponible" in capsys.readouterr().out


def test_puerta_pasa_si_igual_o_instalada_mayor(monkeypatch):
    for tienda in ((2, 2, 1, 0), (2, 1, 0, 0)):
        _instalar_escenario(monkeypatch, (2, 2, 1, 0), tienda)
        assert s50store.puerta_update_obligatorio(store_product_id="9NX") is False


def test_puerta_fail_open_sin_paquete_o_sin_catalogo(monkeypatch):
    # sin identidad de paquete
    monkeypatch.setattr(s50store, "package_full_name", MagicMock(return_value=None))
    consultar = MagicMock()
    monkeypatch.setattr(s50store, "version_tienda", consultar)
    assert s50store.puerta_update_obligatorio(store_product_id="9NX") is False
    consultar.assert_not_called()

    # catálogo no responde
    _instalar_escenario(monkeypatch, (2, 2, 1, 0), None)
    assert s50store.puerta_update_obligatorio(store_product_id="9NX") is False


def test_puerta_sin_store_product_id_no_consulta(monkeypatch):
    _instalar_escenario(monkeypatch, (2, 2, 1, 0), (9, 9, 9, 9))

    assert s50store.puerta_update_obligatorio(nombre_app="s50info") is False
