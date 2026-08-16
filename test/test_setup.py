"""
Tests para el módulo s50setup.py (asistente de configuración inicial SAGE50).
"""

import configparser
from pathlib import Path

import pytest

from s50setup import (
    SAGE50_DOWNLOAD_URL,
    asistente_terminal,
    buscar_terminales_en,
    construir_menu,
    detectar_terminales,
    es_terminal_valido,
    guardar_terminal,
    necesita_asistente,
    terminal_configurado,
)


@pytest.fixture
def terminal_dir(tmp_path):
    """Carpeta de terminal SAGE50 válida (contiene config.ini)."""
    base = tmp_path / "Sage50"
    term = base / "Sage50Term"
    term.mkdir(parents=True)
    (term / "config.ini").write_text(
        f"[API]\nterminal = {term}\n", encoding="utf-8"
    )
    return term


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "appdata" / "s50info" / "config.ini"


class TestEsTerminalValido:
    def test_valido_cuando_contiene_config_ini(self, terminal_dir):
        assert es_terminal_valido(terminal_dir) is True

    def test_invalido_cuando_falta_config_ini(self, tmp_path):
        carpeta = tmp_path / "vacia"
        carpeta.mkdir()
        assert es_terminal_valido(carpeta) is False

    def test_invalido_si_no_existe(self, tmp_path):
        assert es_terminal_valido(tmp_path / "no_existe") is False

    def test_invalido_si_es_archivo(self, tmp_path):
        archivo = tmp_path / "config.ini"
        archivo.write_text("[API]\n", encoding="utf-8")
        assert es_terminal_valido(archivo) is False


class TestTerminalConfigurado:
    def test_devuelve_terminal_configurado(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("[API]\nterminal = C:\\Sage50\\Sage50Term\n", encoding="utf-8")
        assert terminal_configurado(config_path) == "C:\\Sage50\\Sage50Term"

    def test_cadena_vacia_si_no_hay_terminal(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("[API]\ndriver_servidor = x\n", encoding="utf-8")
        assert terminal_configurado(config_path) == ""

    def test_cadena_vacia_si_no_existe_archivo(self, config_path):
        assert terminal_configurado(config_path) == ""


class TestNecesitaAsistente:
    def test_true_si_no_existe_config(self, config_path):
        assert necesita_asistente(config_path) is True

    def test_true_si_config_vacio(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
        assert necesita_asistente(config_path) is True

    def test_true_si_terminal_no_valido(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("[API]\nterminal = C:\\ruta\\inexistente\n", encoding="utf-8")
        assert necesita_asistente(config_path) is True

    def test_false_si_terminal_valido(self, config_path, terminal_dir):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(f"[API]\nterminal = {terminal_dir}\n", encoding="utf-8")
        assert necesita_asistente(config_path) is False


class TestGuardarTerminal:
    def test_crea_seccion_api_si_no_existe(self, config_path):
        guardar_terminal(config_path, Path("C:/Sage50/Sage50Term"))
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        assert parser["API"]["terminal"] == "C:/Sage50/Sage50Term"

    def test_actualiza_terminal_existente(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            "[API]\nterminal = C:\\viejo\nnombre_usuario = sage50\n"
            "[CONFIG_SAGE50]\nempresa = ACME\n",
            encoding="utf-8",
        )
        guardar_terminal(config_path, Path("C:/nuevo/term"))
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        assert parser["API"]["terminal"] == "C:/nuevo/term"
        assert parser["API"]["nombre_usuario"] == "sage50"
        assert parser["CONFIG_SAGE50"]["empresa"] == "ACME"


class TestBuscarTerminales:
    def test_encuentra_subcarpetas_con_config_ini(self, tmp_path):
        (tmp_path / "Sage50Term").mkdir()
        (tmp_path / "Sage50Term" / "config.ini").write_text("", encoding="utf-8")
        (tmp_path / "otros").mkdir()
        encontrados = buscar_terminales_en(tmp_path)
        assert tmp_path / "Sage50Term" in encontrados

    def test_ignora_carpetas_sin_config_ini(self, tmp_path):
        (tmp_path / "vacia").mkdir()
        assert buscar_terminales_en(tmp_path) == []

    def test_base_inexistente_devuelve_vacio(self, tmp_path):
        assert buscar_terminales_en(tmp_path / "no_existe") == []

    def test_detectar_terminales_combina_fuentes(self, tmp_path, monkeypatch):
        (tmp_path / "Term").mkdir()
        (tmp_path / "Term" / "config.ini").write_text("", encoding="utf-8")
        monkeypatch.setattr("s50setup.buscar_en_registro", lambda: [tmp_path])
        monkeypatch.setattr("s50setup.rutas_tipicas", list)
        encontrados = detectar_terminales()
        assert tmp_path / "Term" in encontrados


class TestConstruirMenu:
    def test_menu_con_candidatos(self):
        opciones, _texto = construir_menu([Path("C:/Sage50/Sage50Term")])
        acciones = [accion for accion, _ in opciones]
        assert acciones[0] == "usar"
        assert "manual" in acciones
        assert "descargar" in acciones
        assert acciones[-1] == "salir"

    def test_menu_sin_candidatos(self):
        opciones, _texto = construir_menu([])
        acciones = [accion for accion, _ in opciones]
        assert "usar" not in acciones
        assert acciones == ["manual", "descargar", "salir"]

    def test_menu_muestra_url_descarga(self):
        _opciones, texto = construir_menu([])
        assert SAGE50_DOWNLOAD_URL in texto


class TestAsistenteTerminal:
    def _fakes(self, candidatos=(), elecciones=(), rutas=(), mostrar=None):
        descargas = []
        abrir_url = descargas.append
        elegir = lambda mensaje, choices: elecciones.pop(0)
        pedir_ruta = lambda mensaje: rutas.pop(0) if rutas else ""
        detectar = lambda: list(candidatos)
        return {
            "detectar": detectar,
            "elegir": elegir,
            "pedir_ruta": pedir_ruta,
            "abrir_url": abrir_url,
            "mostrar": mostrar or (lambda *a, **k: None),
        }, descargas

    def test_usa_candidato_detectado(self, config_path, terminal_dir):
        fakes, descargas = self._fakes(
            candidatos=[terminal_dir], elecciones=["1"]
        )
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado == terminal_dir
        assert terminal_configurado(config_path) == str(terminal_dir)
        assert descargas == []

    def test_ruta_manual_valida(self, config_path, terminal_dir):
        fakes, _ = self._fakes(elecciones=["1"], rutas=[str(terminal_dir)])
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado == terminal_dir
        assert terminal_configurado(config_path) == str(terminal_dir)

    def test_ruta_manual_acepta_propio_config_ini(self, config_path, terminal_dir):
        fakes, _ = self._fakes(elecciones=["1"], rutas=[str(terminal_dir / "config.ini")])
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado == terminal_dir

    def test_ruta_manual_invalida_reintenta_y_sale(self, config_path, tmp_path):
        mala = tmp_path / "sin_config"
        mala.mkdir()
        # Sin candidatos: 1=manual, 2=descargar, 3=salir
        fakes, _ = self._fakes(elecciones=["1", "3"], rutas=[str(mala)])
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado is None

    def test_descargar_abre_url_y_continua(self, config_path):
        # Sin candidatos: 1=manual, 2=descargar, 3=salir
        fakes, descargas = self._fakes(elecciones=["2", "3"])
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado is None
        assert descargas == [SAGE50_DOWNLOAD_URL]

    def test_salir_devuelve_none_sin_guardar(self, config_path):
        fakes, _ = self._fakes(elecciones=["3"])
        resultado = asistente_terminal(config_path, **fakes)
        assert resultado is None
        assert terminal_configurado(config_path) == ""

    def test_eof_devuelve_none(self, config_path):
        def elegir_eof(mensaje, choices):
            raise EOFError

        resultado = asistente_terminal(
            config_path,
            detectar=list,
            elegir=elegir_eof,
            pedir_ruta=lambda mensaje: "",
            abrir_url=lambda url: None,
            mostrar=lambda *a, **k: None,
        )
        assert resultado is None
