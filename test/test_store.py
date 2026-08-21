"""Tests de s50store: puerta de actualización obligatoria vía DisplayCatalog."""

import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import s50store  # noqa: E402


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


# --- puerta de bloqueo --------------------------------------------------


def _instalar_escenario(monkeypatch, instalada, tienda):
    monkeypatch.setattr(s50store, "package_full_name", MagicMock(return_value="InfoMSD.s50info_2.2.1.0_neutral__x"))
    monkeypatch.setattr(s50store, "version_de_full_name", MagicMock(return_value=instalada))
    monkeypatch.setattr(s50store, "version_tienda", MagicMock(return_value=tienda))
    abrir = MagicMock()
    monkeypatch.setattr(s50store, "abrir_tienda", abrir)
    return abrir


def test_puerta_bloquea_cuando_la_tienda_es_mayor(monkeypatch, capsys):
    abrir = _instalar_escenario(monkeypatch, (2, 2, 1, 0), (2, 3, 0, 0))

    assert s50store.puerta_update_obligatorio(nombre_app="s50info", store_product_id="9NX") is True
    abrir.assert_called_once()
    salida = capsys.readouterr().out
    assert "obligatoria" in salida and "s50info" in salida


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
