import importlib.util
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "msix" / "build_msix.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_msix", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_branded_assets_are_generated_and_referenced_by_manifest(tmp_path):
    builder = load_builder()
    source = ROOT / "img" / "store" / "box_1x1_2160.png"

    builder.write_assets(tmp_path, source)
    builder.write_manifest(
        tmp_path,
        package_name="InfoMSD.s50info",
        publisher="CN=publisher",
        version="1.2.3.0",
        display_name="s50info",
        publisher_display_name="InfoMSD",
    )

    with Image.open(source) as original:
        source_thumbnail = original.convert("RGBA").resize((44, 44), Image.Resampling.LANCZOS)
    for filename, expected_size in (
        ("Square44x44Logo.png", (44, 44)),
        ("Square150x150Logo.png", (150, 150)),
    ):
        with Image.open(tmp_path / "Assets" / filename) as asset:
            assert asset.size == expected_size
            assert len(asset.convert("RGB").getcolors(maxcolors=expected_size[0] * expected_size[1])) > 1

    with Image.open(tmp_path / "Assets" / "Square44x44Logo.png") as small_asset:
        assert ImageChops.difference(small_asset.convert("RGBA"), source_thumbnail).getbbox() is None

    manifest = ElementTree.parse(tmp_path / "AppxManifest.xml")
    namespace = {
        "appx": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    }
    properties_logo = manifest.findtext("appx:Properties/appx:Logo", namespaces=namespace)
    visual = manifest.find("appx:Applications/appx:Application/uap:VisualElements", namespace)
    assert properties_logo == r"Assets\Square150x150Logo.png"
    assert visual.attrib["Square44x44Logo"] == r"Assets\Square44x44Logo.png"
    assert visual.attrib["Square150x150Logo"] == r"Assets\Square150x150Logo.png"


def test_asset_generation_fails_when_branded_source_is_missing(tmp_path):
    builder = load_builder()

    with pytest.raises(SystemExit, match="Branded Store asset source not found"):
        builder.write_assets(tmp_path, tmp_path / "missing.png")


def test_copy_scripts_folder_ships_examples_into_staging(tmp_path):
    builder = load_builder()
    scripts_dir = tmp_path / "script"
    scripts_dir.mkdir()
    (scripts_dir / "ejemplo.py").write_text("print('hola')\n", encoding="utf-8")

    builder.copy_scripts_folder(scripts_dir, tmp_path / "staging")

    shipped = tmp_path / "staging" / "script" / "ejemplo.py"
    assert shipped.is_file()
    assert shipped.read_text(encoding="utf-8") == "print('hola')\n"


def test_copy_scripts_folder_ignores_pycache(tmp_path):
    builder = load_builder()
    scripts_dir = tmp_path / "script"
    (scripts_dir / "__pycache__").mkdir(parents=True)
    (scripts_dir / "hola.py").write_text("print('hola')\n", encoding="utf-8")
    (scripts_dir / "__pycache__" / "hola.cpython-313.pyc").write_bytes(b"\x00")

    builder.copy_scripts_folder(scripts_dir, tmp_path / "staging")

    staged_script = tmp_path / "staging" / "script"
    assert (staged_script / "hola.py").is_file()
    assert not (staged_script / "__pycache__").exists()


def test_copy_scripts_folder_fails_when_missing(tmp_path):
    builder = load_builder()

    with pytest.raises(SystemExit, match="Scripts folder not found"):
        builder.copy_scripts_folder(tmp_path / "missing", tmp_path / "staging")


def test_default_output_dir_is_exclusive_msix_folder():
    builder = load_builder()

    assert builder.DEFAULT_OUTPUT_DIR == r"D:\c\msix"


def test_staging_dir_is_isolated_from_repo_msix_source(tmp_path, monkeypatch):
    builder = load_builder()
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    staging = builder.create_staging_directory()

    assert staging.is_dir()
    assert not any(staging.iterdir()), "staging debe empezar vacío"
    assert staging.resolve() != BUILDER_PATH.parent.resolve(), (
        "staging nunca debe ser el directorio fuente msix/ del repo"
    )
    assert staging.resolve().is_relative_to(tmp_path.resolve())
