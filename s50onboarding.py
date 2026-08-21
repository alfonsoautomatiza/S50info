"""Onboarding HTML de primera ejecución y novedades para S50Info.

Se muestra una vez por versión: página completa en la primera ejecución y
página de novedades tras cada actualización. La página es autocontenida
(CSS inline, fuentes del sistema, sin red) y se abre en el navegador por
defecto. El estado se guarda en `onboarding.json` dentro del estado de la
app (mismo patrón que usage_prompt.json).

Register visual (heredado del CLI): verde fósforo = bienvenida/estado,
ámbar = novedades; mundo terminal oscuro. Un solo acento por página.
"""

import json
import logging
import os
import re
import sys
import urllib.request
import webbrowser
from html import escape
from html.parser import HTMLParser
from pathlib import Path

_logger = logging.getLogger(__name__)

ONBOARDING_FILE = "onboarding.json"
MANUAL_URL = "https://sage50eia.com/s50info"
SAGE50BI_URL = "https://www.alfonsoautomatiza.com/s50-bi"
NOVEDADES_URL = "https://github.com/alfonsoautomatiza/S50info/releases"
NOVEDADES_PAGE_URL = "https://alfonsoautomatiza.github.io/S50info/novedades/"

# Fallback offline de las novedades: la fuente canónica es NOVEDADES_PAGE_URL,
# cuya sección por versión se embebe en la página de actualización.
# Formato: texto plano; `texto` se renderiza como comando.
CHANGELOG: dict[str, list[str]] = {
    "2.2.1": [
        "Nuevo comando `manual` (o `--m` / `-m`): abre el manual en el navegador.",
        "Nuevo comando `version` (o `--v` / `-v`): muestra la versión instalada.",
        "Si te equivocas con un comando, se recuerda cómo ver la ayuda (`-h`).",
        "Onboarding en HTML: esta misma página de novedades en cada actualización.",
    ],
}

_ACENTO = {
    "first": ("#2ea043", "#388bfd", "Bienvenido a"),
    "update": ("#bb8009", "#bb8009", "Novedades en"),
}


def _estado_path(state_dir: Path) -> Path:
    return Path(state_dir) / ONBOARDING_FILE


def _leer_estado(path: Path) -> dict:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _logger.warning("onboarding: estado ilegible (%s): %s", path, exc)
    return {}


def _guardar_estado(path: Path, estado: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(estado, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        _logger.warning("onboarding: no se pudo guardar estado (%s): %s", path, exc)
        return False


def tipo_a_mostrar(estado: dict, version: str | None = None) -> str | None:
    """Devuelve "first" (primera vez), "update" (nueva versión) o None."""
    from s50version import __version__

    version = version or __version__
    if not estado:
        return "first"
    if estado.get("version_seen") != version:
        return "update"
    return None


def _formatear_entrada(mensaje: str) -> str:
    partes = escape(mensaje).split("`")
    resultado = []
    for i, parte in enumerate(partes):
        resultado.append(f"<code>{parte}</code>" if i % 2 == 1 else parte)
    return "".join(resultado)


class _ExtractorSeccionVersion(HTMLParser):
    """Extrae el HTML interno de la sección <h2 id="X.Y.Z"> de la página MkDocs.

    Estado: esperando → en_h2 (titulo de la versión) → capturando → fin
    (al llegar al siguiente <h2> o al cierre del <article>).
    """

    _SALTAR_TAGS = {"script", "style", "nav", "footer"}

    def __init__(self, objetivo: str):
        super().__init__(convert_charrefs=True)
        self._objetivo = objetivo
        self._estado = "esperando"
        self._saltando: list[str] = []
        self._trozos: list[str] = []

    def _empezar_salto(self, tag: str) -> None:
        self._saltando.append(tag)

    def handle_starttag(self, tag, attrs):
        if self._saltando:
            if tag not in self.VOID_ELEMENTS and tag == self._saltando[-1]:
                self._saltando.append(tag)
            return
        if self._estado == "fin":
            return
        if tag == "h2":
            if self._estado == "capturando":
                self._estado = "fin"
            elif dict(attrs).get("id") == self._objetivo:
                self._estado = "en_h2"
            return
        if self._estado == "capturando":
            clases = dict(attrs).get("class", "")
            if tag in self._SALTAR_TAGS or "headerlink" in clases:
                self._empezar_salto(tag)
                return
            if tag in ("nav", "article"):
                self._estado = "fin"
                return
            self._trozos.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self._saltando:
            if tag == self._saltando[-1]:
                self._saltando.pop()
            return
        if self._estado == "fin":
            return
        if self._estado == "en_h2" and tag == "h2":
            self._estado = "capturando"
            return
        if self._estado == "capturando":
            if tag == "article":
                self._estado = "fin"
                return
            if tag not in self._SALTAR_TAGS:
                self._trozos.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        if self._saltando or self._estado != "capturando":
            return
        self._trozos.append(self.get_starttag_text())

    def handle_data(self, data):
        if self._estado == "capturando" and not self._saltando:
            self._trozos.append(data)

    @property
    def html(self) -> str | None:
        return "".join(self._trozos).strip() or None


def _extraer_seccion_version(pagina_html: str, version: str) -> str | None:
    """Devuelve el HTML de la sección de `version` de la página de novedades."""
    objetivo = re.sub(r"[^0-9A-Za-z]", "", version)
    if not objetivo:
        return None
    extractor = _ExtractorSeccionVersion(objetivo)
    try:
        extractor.feed(pagina_html)
        extractor.close()
    except Exception as exc:  # HTML malformado: tolerar y caer al fallback
        _logger.warning("onboarding: página de novedades ilegible: %s", exc)
        return None
    return extractor.html


def _descargar_pagina_novedades(timeout: float = 4.0) -> str:
    """Descarga la página canónica de novedades (tests: monkeypatch)."""
    with urllib.request.urlopen(NOVEDADES_PAGE_URL, timeout=timeout) as respuesta:
        return respuesta.read().decode("utf-8", errors="replace")


def _seccion_novedades(version: str) -> str | None:
    """Sección de novedades de la versión, embebida desde la página oficial."""
    try:
        pagina = _descargar_pagina_novedades()
    except (OSError, ValueError) as exc:
        _logger.info("onboarding: novedades remotas no disponibles: %s", exc)
        return None
    return _extraer_seccion_version(pagina, version)


def _css(acento: str, acento_hover: str) -> str:
    return f"""
    :root {{
      color-scheme: dark;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html {{ scrollbar-gutter: stable; }}
    body {{
      font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #0b0f14;
      color: #c9d3dc;
      line-height: 1.65;
      -webkit-font-smoothing: antialiased;
      min-height: 100vh;
    }}
    code, .mono {{ font-family: "Cascadia Code", Consolas, "JetBrains Mono", monospace; }}
    .pagina {{ max-width: 860px; margin: 0 auto; padding: 56px 28px 40px; }}
    .prompt {{
      display: inline-flex; align-items: center; gap: 10px;
      font-size: 15px; color: #8b98a5;
      background: #10161d; border-radius: 8px;
      padding: 8px 14px; margin-bottom: 36px;
    }}
    .prompt code {{ color: {acento}; }}
    .cursor {{
      display: inline-block; width: 8px; height: 17px;
      background: {acento}; margin-left: 2px;
      animation: parpadeo 1.1s steps(1) infinite;
      vertical-align: text-bottom;
    }}
    @keyframes parpadeo {{ 50% {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .cursor {{ animation: none; }}
      * {{ transition: none !important; }}
    }}
    .version-pill {{
      display: inline-block; font-size: 13px; font-weight: 600;
      color: {acento}; border: 1px solid {acento}55;
      padding: 2px 12px; border-radius: 999px; margin-left: 10px;
      vertical-align: middle; letter-spacing: 0.02em;
    }}
    h1 {{
      font-size: clamp(28px, 5vw, 40px); font-weight: 650;
      letter-spacing: -0.02em; line-height: 1.15;
      color: #e8edf2; margin: 0 0 14px;
      text-wrap: balance; max-width: 22ch;
    }}
    .sub {{ font-size: 17px; color: #8b98a5; max-width: 58ch; margin-bottom: 44px; }}
    h2 {{
      font-size: 14px; font-weight: 600; letter-spacing: 0.08em;
      text-transform: uppercase; color: #768390;
      margin: 44px 0 16px;
    }}
    .comandos {{ border-collapse: collapse; width: 100%; }}
    .comandos td {{
      padding: 11px 0; border-bottom: 1px solid #1a2230;
      vertical-align: baseline;
    }}
    .comandos tr:last-child td {{ border-bottom: none; }}
    .comandos code {{
      color: {acento}; font-size: 14.5px; white-space: nowrap;
      padding-right: 28px;
    }}
    .comandos .desc {{ color: #a9b4bf; font-size: 15px; }}
    .sugerencias {{ display: grid; gap: 14px; }}
    .sugerencia {{
      background: #10161d; border-radius: 14px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
      padding: 18px 20px;
    }}
    .sugerencia p {{ color: #a9b4bf; font-size: 14.5px; margin-bottom: 10px; }}
    .linea-cmd {{
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      background: #0b0f14; border-radius: 8px; padding: 10px 14px;
    }}
    .linea-cmd code {{ color: #e8edf2; font-size: 13.5px; overflow-x: auto; }}
    .copiar {{
      flex: none; font: 600 12px/1 -apple-system, "Segoe UI", Roboto, sans-serif;
      color: #8b98a5; background: transparent;
      border: 1px solid #2a3441; border-radius: 6px;
      padding: 6px 12px; cursor: pointer;
      transition: color 120ms, border-color 120ms, background 120ms;
    }}
    .copiar:hover {{ color: #e8edf2; border-color: #3d4a5a; background: #151c26; }}
    .copiar:focus-visible {{ outline: 2px solid {acento}; outline-offset: 2px; }}
    .copiar.ok {{ color: {acento}; border-color: {acento}55; }}
    .acciones {{ display: flex; flex-wrap: wrap; gap: 14px; margin-top: 44px; }}
    .btn {{
      display: inline-block; font-size: 15px; font-weight: 600;
      text-decoration: none; border-radius: 8px; padding: 11px 22px;
      transition: background 120ms;
    }}
    .btn-primario {{ background: {acento}; color: #ffffff; }}
    .btn-primario:hover {{ background: {acento_hover}; }}
    .btn-secundario {{ color: #c9d3dc; border: 1px solid #2a3441; }}
    .btn-secundario:hover {{ background: #151c26; border-color: #3d4a5a; }}
    .btn:focus-visible {{ outline: 2px solid {acento}; outline-offset: 2px; }}
    .bi {{
      margin-top: 56px; padding-top: 22px; border-top: 1px solid #1a2230;
      font-size: 14.5px; color: #8b98a5;
    }}
    ul.changelog {{
      list-style: none; max-width: 62ch;
    }}
    ul.changelog li {{
      position: relative; padding: 9px 0 9px 26px;
      color: #a9b4bf; font-size: 15px;
      border-bottom: 1px solid #161d29;
    }}
    ul.changelog li:last-child {{ border-bottom: none; }}
    ul.changelog li::before {{
      content: ""; position: absolute; left: 2px; top: 17px;
      width: 8px; height: 8px; border-radius: 1px;
      background: {acento}; opacity: 0.85;
      transform: rotate(45deg);
    }}
    ul.changelog code {{
      color: {acento}; font-size: 13.5px;
    }}
    .novedades h3 {{
      font-size: 14px; font-weight: 600; letter-spacing: 0.08em;
      text-transform: uppercase; color: #768390; margin: 30px 0 12px;
    }}
    .novedades p {{ color: #a9b4bf; font-size: 15px; margin: 8px 0; }}
    .novedades ul {{ list-style: none; }}
    .novedades li {{
      position: relative; padding: 8px 0 8px 24px;
      color: #a9b4bf; font-size: 15px;
      border-bottom: 1px solid #161d29;
    }}
    .novedades li:last-child {{ border-bottom: none; }}
    .novedades li::before {{
      content: ""; position: absolute; left: 1px; top: 16px;
      width: 8px; height: 8px; border-radius: 1px;
      background: {acento}; opacity: 0.85; transform: rotate(45deg);
    }}
    .novedades code {{ color: {acento}; font-size: 13.5px; }}
    .novedades strong {{ color: #e8edf2; }}
    .fuente {{ margin-top: 14px; font-size: 13px; color: #6e7b89; }}
    .fuente a {{ color: #58a6ff; text-decoration: none; }}
    .fuente a:hover {{ text-decoration: underline; }}
    .sub a, .bi a {{ color: #58a6ff; }}
    .bi a {{ color: #58a6ff; text-decoration: none; font-weight: 600; }}
    .bi a:hover {{ text-decoration: underline; }}
    .pie {{
      margin-top: 26px; font-size: 13px; color: #6e7b89;
      display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    }}
    @media (max-width: 560px) {{
      .pagina {{ padding: 36px 20px 28px; }}
      .comandos, .comandos tbody, .comandos tr, .comandos td {{ display: block; width: 100%; }}
      .comandos tr {{ padding: 10px 0; }}
      .comandos code {{ display: block; padding: 0 0 4px; white-space: normal; }}
      .comandos .desc {{ font-size: 14px; }}
    }}
    """.strip()


def _comandos() -> list[tuple[str, str]]:
    return [
        ("s50info info", "Ver la configuración activa: servidor SQL, empresa, comunes y años."),
        ("s50info sql \"…\"", "Consultar con SQL de lectura y sintaxis SAGE50 (`#clientes`, `[COMU]tabla`)."),
        ("s50info export \"…\"", "Exportar el resultado a Excel, CSV, JSON, XML o TXT."),
        ("s50info run script.py", "Automatizar: ejecutar tus scripts Python con la conexión preparada."),
    ]


def _sugerencias() -> list[tuple[str, str, str]]:
    return [
        (
            "Tu primera consulta",
            "Las tablas de gestión se escriben con # y se resuelven al ejercicio activo.",
            's50info sql "select codigo, nombre from #clientes"',
        ),
        (
            "Llévalo a Excel",
            "Exporta cualquier consulta a xlsx en la carpeta de resultados.",
            's50info export "select codigo, nombre from #articulo" --formato xlsx',
        ),
    ]


def render_html(tipo: str, version: str) -> str:
    """Genera la página autocontenida de onboarding (first) o novedades (update)."""
    acento, acento_hover, titulo = _ACENTO[tipo]
    version_esc = escape(version)

    if tipo == "first":
        titulo_h1 = "Consulta, exporta y automatiza tu SAGE50 desde la línea de comandos."
        intro = (
            "<p class=\"sub\">Sin abrir herramientas pesadas: conexión, consulta, "
            "exportación y automatización en un único comando portable.</p>"
        )
        cuerpo = _seccion_comandos() + _seccion_sugerencias()
    else:
        titulo_h1 = "Se instaló una nueva versión de s50info"
        intro = ""
        cuerpo = _seccion_changelog(version)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>s50info · {version_esc}</title>
<style>{_css(acento, acento_hover)}</style>
</head>
<body>
<!--
THESIS: A release note you can act on — the terminal session continues in the browser,
refusing the generic marketing welcome card.
OWN-WORLD: dark terminal ground, one semantic accent (green=welcome, amber=update),
mono reserved for real commands, single hairline sections, one authored blink.
STORY: the reader learns what s50info does, copies two starter commands, opens the manual.
FIRST VIEWPORT: prompt chip with blinking cursor + version pill, balanced headline,
one-line promise; primary action (manual) below the fold after two copyable tips.
FORM: extension of the CLI onboarding surface inside its established world; no seed roll.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md
-->
<div class="pagina">
  <div class="prompt">C:\\&gt;&nbsp;<code>s50info</code><span class="cursor" aria-hidden="true"></span>
    <span class="version-pill">v{version_esc}</span>
  </div>
  <h1>{escape(titulo_h1)}</h1>
  {intro}
  {cuerpo}
  <div class="acciones">
    <a class="btn btn-primario" href="{MANUAL_URL}" target="_blank" rel="noopener">Abrir el manual</a>
    <a class="btn btn-secundario" href="{NOVEDADES_PAGE_URL}" target="_blank" rel="noopener">Ver todas las novedades</a>
  </div>
  <div class="bi">
    ¿Informes y cuadros de mando visuales, sin comandos? Conoce
    <a href="{SAGE50BI_URL}" target="_blank" rel="noopener">Sage50BI</a>,
    otro producto para perfiles no técnicos.
  </div>
  <div class="pie">
    <span>Este aviso se muestra una sola vez por versión.</span>
    <span class="mono">s50info v{version_esc}</span>
  </div>
</div>
<script>
  document.querySelectorAll("[data-copiar]").forEach(function (boton) {{
    boton.addEventListener("click", function () {{
      var texto = boton.getAttribute("data-copiar");
      function ok() {{
        boton.textContent = "¡Copiado!";
        boton.classList.add("ok");
        setTimeout(function () {{
          boton.textContent = "Copiar";
          boton.classList.remove("ok");
        }}, 1400);
      }}
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(texto).then(ok);
      }} else {{
        var tmp = document.createElement("textarea");
        tmp.value = texto;
        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand("copy");
        document.body.removeChild(tmp);
        ok();
      }}
    }});
  }});
</script>
</body>
</html>"""


def _seccion_comandos() -> str:
    filas = "".join(
        f"<tr><td><code>{escape(cmd)}</code></td><td class=\"desc\">{escape(desc)}</td></tr>"
        for cmd, desc in _comandos()
    )
    return (
        f"<h2>Qué puedes hacer</h2>"
        f"<table class=\"comandos\"><tbody>{filas}</tbody></table>"
    )


def _seccion_sugerencias() -> str:
    sugerencias = "".join(
        f"""
        <div class="sugerencia">
          <p><strong>{escape(titulo)}</strong> — {escape(desc)}</p>
          <div class="linea-cmd">
            <code>{escape(cmd)}</code>
            <button class="copiar" type="button" data-copiar="{escape(cmd)}">Copiar</button>
          </div>
        </div>
        """
        for titulo, desc, cmd in _sugerencias()
    )
    return f"<h2>Sugerencias para empezar</h2><div class=\"sugerencias\">{sugerencias}</div>"


def _seccion_changelog(version: str) -> str:
    remota = _seccion_novedades(version)
    if remota:
        fuente = (
            f'<p class="fuente">Fuente: <a href="{NOVEDADES_PAGE_URL}" '
            'target="_blank" rel="noopener">Novedades del manual</a></p>'
        )
        return (
            '<h2>Novedades en esta versión</h2>'
            f'<div class="novedades">{remota}</div>{fuente}'
        )
    entradas = CHANGELOG.get(version)
    if entradas:
        items = "".join(f"<li>{_formatear_entrada(e)}</li>" for e in entradas)
        lista = f"<ul class=\"changelog\">{items}</ul>"
    else:
        lista = (
            f"<p class=\"sub\">Consulta el detalle de la versión en las "
            f"<a href=\"{NOVEDADES_URL}\" target=\"_blank\" rel=\"noopener\">releases de GitHub</a>.</p>"
        )
    return f"<h2>Novedades en esta versión</h2>{lista}"


def _abrir_html(path: Path) -> None:
    """Abre el fichero HTML generado en el navegador por defecto (robusto frozen)."""
    startfile = getattr(os, "startfile", None)
    if sys.platform == "win32" and startfile is not None:
        try:
            startfile(str(path))
            return
        except OSError:
            _logger.warning("onboarding: os.startfile falló para %s; pruebo webbrowser", path)
    try:
        webbrowser.open(path.resolve().as_uri())
    except (OSError, webbrowser.Error):
        _logger.warning("onboarding: no se pudo abrir %s", path)


def mostrar_if_necesario(
    state_dir: Path,
    *,
    version: str | None = None,
    stdout_isatty: bool | None = None,
    abrir=None,
) -> str | None:
    """Genera y abre la página correspondiente una sola vez por versión.

    Devuelve el tipo mostrado ("first" o "update"), o None si no corresponde.
    No abre nada si stdout no es una terminal (evita navegadores en pipelines).
    """
    if stdout_isatty is None:
        stdout_isatty = sys.stdout.isatty()
    if not stdout_isatty:
        return None

    from s50version import __version__

    version = version or __version__
    path = _estado_path(state_dir)
    estado = _leer_estado(path)
    tipo = tipo_a_mostrar(estado, version)
    if tipo is None:
        return None

    destino = Path(state_dir) / "onboarding" / f"onboarding_{tipo}_v{version}.html"
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(render_html(tipo, version), encoding="utf-8")
    except OSError as exc:
        _logger.warning("onboarding: no se pudo generar la página (%s): %s", destino, exc)
        return None

    (abrir or _abrir_html)(destino)
    _guardar_estado(path, {"version_seen": version})
    return tipo
