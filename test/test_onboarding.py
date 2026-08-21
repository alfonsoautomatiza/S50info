"""Tests del onboarding HTML de s50info (primera ejecución y actualizaciones)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import s50onboarding  # noqa: E402


# --- decisión de tipo -------------------------------------------------


def test_tipo_a_mostrar_first_update_y_none():
    assert s50onboarding.tipo_a_mostrar({}, "2.2.1") == "first"
    assert s50onboarding.tipo_a_mostrar({"version_seen": "2.2.0"}, "2.2.1") == "update"
    assert s50onboarding.tipo_a_mostrar({"version_seen": "2.2.1"}, "2.2.1") is None


# --- HTML primera ejecución -------------------------------------------


def test_render_first_html_resumen_comandos_manual_y_sugerencias():
    html = s50onboarding.render_html("first", "2.2.1")

    assert html.lstrip().lower().startswith("<!doctype html")
    # Resumen de qué hace la aplicación
    assert "línea de comandos" in html
    assert "exportar" in html.lower()
    # Comandos reales del producto
    for comando in ("info", "sql", "export", "run"):
        assert f"s50info {comando}" in html
    # Par de sugerencias para empezar
    assert "Sugerencias" in html
    assert html.count("data-copiar") >= 2
    # Enlace a la ayuda (manual) y botón secundario a la página de novedades
    assert s50onboarding.MANUAL_URL in html
    assert s50onboarding.NOVEDADES_PAGE_URL in html
    # Llamada sutil a Sage50BI como otro producto
    assert "otro producto" in html
    assert s50onboarding.SAGE50BI_URL in html
    # Versión visible
    assert "2.2.1" in html
    # Autocontenida: sin ficheros externos de estilos ni fuentes remotas
    assert "<link" not in html
    assert "http" not in html.split("</style>")[0].replace("http://www.w3.org", "")


def test_render_first_html_escapa_version():
    html = s50onboarding.render_html("first", '2.2.<script>"')

    assert "<script>\"" not in html
    assert "&lt;script&gt;" in html


# --- HTML actualización -----------------------------------------------


def test_extraer_seccion_version_desde_pagina_mkdocs():
    pagina = (
        "<h1>Novedades</h1>"
        '<h2 id="220"><a class="headerlink" href="#220">¶</a></h2>'
        "<p>Vieja</p>"
        '<h2 id="221">2.2.1<a class="headerlink" href="#221" title="Permanent link">¶</a></h2>'
        "<p><strong>Fecha:</strong> agosto 2026</p>"
        "<h3>Cambios principales<a class=\"headerlink\" href=\"#cambios\">¶</a></h3>"
        "<ul><li>Nuevo comando <code>manual</code></li></ul>"
        '<h2 id="222">Siguiente</h2><p>Posterior</p>'
    )

    seccion = s50onboarding._extraer_seccion_version(pagina, "2.2.1")

    assert seccion is not None
    assert "<strong>Fecha:</strong>" in seccion
    assert "Nuevo comando" in seccion
    assert "headerlink" not in seccion
    assert "Vieja" not in seccion
    assert "Posterior" not in seccion
    assert "Siguiente" not in seccion


def test_extraer_seccion_version_ultima_h2_para_al_final_del_articulo():
    pagina = (
        '<h2 id="221">2.2.1</h2><p>Contenido</p></article>'
        "<nav>Volver al principio</nav>"
    )

    seccion = s50onboarding._extraer_seccion_version(pagina, "2.2.1")

    assert seccion is not None
    assert "Contenido" in seccion
    assert "Volver" not in seccion


def test_extraer_seccion_version_inexistente_devuelve_none():
    assert s50onboarding._extraer_seccion_version("<h2 id='otra'>x</h2>", "9.9.9") is None


def test_seccion_novedades_sin_red_devuelve_none(monkeypatch):
    def falla(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setattr(s50onboarding, "_descargar_pagina_novedades", falla)

    assert s50onboarding._seccion_novedades("2.2.1") is None


def test_render_update_embebe_novedades_remotas(monkeypatch):
    monkeypatch.setattr(
        s50onboarding, "_seccion_novedades", lambda v: "<p><strong>Fecha:</strong> agosto 2026</p><ul><li>Comando <code>manual</code></li></ul>"
    )

    html = s50onboarding.render_html("update", "2.2.1")

    assert "agosto 2026" in html
    assert s50onboarding.NOVEDADES_PAGE_URL in html
    assert "Fuente:" in html


def test_render_update_html_mismo_estilo_y_changelog(monkeypatch):
    monkeypatch.setattr(s50onboarding, "_seccion_novedades", lambda v: None)

    html = s50onboarding.render_html("update", "2.2.1")

    assert html.lstrip().lower().startswith("<!doctype html")
    assert "Novedades" in html
    assert "2.2.1" in html
    # Mismo estilo: mismos recursos y llamada que first
    assert s50onboarding.MANUAL_URL in html
    assert "otro producto" in html
    assert s50onboarding.SAGE50BI_URL in html
    # Changelog local (fallback) presente en la página
    for entrada in s50onboarding.CHANGELOG.get("2.2.1", []):
        assert entrada.split("`")[0].strip()[:12] in html


def test_render_update_sin_changelog_muestra_link_releases(monkeypatch):
    monkeypatch.setattr(s50onboarding, "_seccion_novedades", lambda v: None)

    html = s50onboarding.render_html("update", "9.9.9")

    assert s50onboarding.NOVEDADES_URL in html


# --- flujo mostrar_if_necesario ---------------------------------------


def test_mostrar_if_necesario_genera_abre_y_guarda(tmp_path):
    abiertos = []

    tipo1 = s50onboarding.mostrar_if_necesario(tmp_path, version="2.2.1", stdout_isatty=True, abrir=abiertos.append)
    tipo2 = s50onboarding.mostrar_if_necesario(tmp_path, version="2.2.1", stdout_isatty=True, abrir=abiertos.append)

    assert tipo1 == "first"
    assert tipo2 is None
    assert len(abiertos) == 1

    pagina = Path(abiertos[0])
    assert pagina.is_file()
    assert pagina.suffix == ".html"
    contenido = pagina.read_text(encoding="utf-8")
    assert "2.2.1" in contenido
    assert "<!DOCTYPE html".upper()[:9] in contenido.upper()[:30]

    estado = json.loads((tmp_path / "onboarding.json").read_text(encoding="utf-8"))
    assert estado == {"version_seen": "2.2.1"}


def test_mostrar_if_necesario_update_reusa_mismo_estilo(tmp_path):
    abiertos = []
    s50onboarding.mostrar_if_necesario(tmp_path, version="2.2.1", stdout_isatty=True, abrir=abiertos.append)
    s50onboarding._guardar_estado(tmp_path / "onboarding.json", {"version_seen": "2.2.0"})
    tipo = s50onboarding.mostrar_if_necesario(tmp_path, version="2.2.1", stdout_isatty=True, abrir=abiertos.append)

    assert tipo == "update"
    contenido = Path(abiertos[1]).read_text(encoding="utf-8")
    assert "Novedades" in contenido


def test_mostrar_if_necesario_no_abre_nada_sin_terminal(tmp_path):
    abiertos = []

    tipo = s50onboarding.mostrar_if_necesario(tmp_path, version="2.2.1", stdout_isatty=False, abrir=abiertos.append)

    assert tipo is None
    assert abiertos == []
    assert not (tmp_path / "onboarding.json").exists()
