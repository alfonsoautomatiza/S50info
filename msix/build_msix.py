#!/usr/bin/env python3
"""Build an MSIX package for Microsoft Partner Center submission."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from PIL import Image, ImageOps


DEFAULT_PACKAGE_NAME = "InfoMSD.s50info"
DEFAULT_PUBLISHER = "CN=D75F3D07-BF68-4BB3-B36C-5A12A1A03277"
DEFAULT_DISPLAY_NAME = "s50info"
DEFAULT_PUBLISHER_DISPLAY_NAME = "InfoMSD"
DEFAULT_BUILD_ROOT = r"D:\c\s50info\dist\s50info.exe"
DEFAULT_OUTPUT_DIR = r"D:\c\msix"
DEFAULT_ASSET_SOURCE = r"img\store\box_1x1_2160.png"
DEFAULT_SCRIPTS_DIR = r"script"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an MSIX package from the PyInstaller output."
    )
    parser.add_argument("--publisher", default=DEFAULT_PUBLISHER)
    parser.add_argument("--display-name", default=DEFAULT_DISPLAY_NAME)
    parser.add_argument("--publisher-display-name", default=DEFAULT_PUBLISHER_DISPLAY_NAME)
    parser.add_argument("--package-name", default=DEFAULT_PACKAGE_NAME)
    parser.add_argument("--build-root", default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--asset-source", default=DEFAULT_ASSET_SOURCE)
    parser.add_argument("--scripts-dir", default=DEFAULT_SCRIPTS_DIR)
    parser.add_argument("--makeappx-path", default="makeappx.exe")
    parser.add_argument("--signtool-path", default="signtool.exe")
    parser.add_argument("--certificate-path", default="")
    parser.add_argument("--certificate-password", default="")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_repo_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def resolve_tool_path(tool_path: str, tool_name: str) -> str:
    """Resolve Windows SDK tools when they are not available in PATH."""
    direct = shutil.which(tool_path)
    if direct:
        return direct

    candidate = Path(tool_path)
    if candidate.is_file():
        return str(candidate)

    if candidate.name.lower() != tool_name.lower():
        return tool_path

    program_files_x86 = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    if not program_files_x86:
        return tool_path

    windows_kits = Path(program_files_x86) / "Windows Kits" / "10"
    bin_dir = windows_kits / "bin"
    if tool_name.lower() == "makeappx.exe":
        app_cert_candidate = windows_kits / "App Certification Kit" / tool_name
        if app_cert_candidate.is_file():
            return str(app_cert_candidate)

    if bin_dir.is_dir():
        version_dirs = sorted((path for path in bin_dir.iterdir() if path.is_dir()), reverse=True)
        for arch in ("x64", "x86"):
            for version_dir in version_dirs:
                sdk_candidate = version_dir / arch / tool_name
                if sdk_candidate.is_file():
                    return str(sdk_candidate)

    return tool_path


def read_msix_version(root: Path) -> str:
    product_path = root / "c" / "product.json"
    try:
        product = json.loads(product_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Product metadata not found: {product_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {product_path}: {exc}") from exc

    version = str(product.get("version", ""))
    parts = version.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise SystemExit(
            f"Invalid product version '{version}'. MSIX build expects X.Y.Z in c/product.json."
        )
    return f"{version}.0"


def write_assets(staging_dir: Path, source_path: Path) -> None:
    if not source_path.is_file():
        raise SystemExit(f"Branded Store asset source not found: {source_path}")

    assets_dir = staging_dir / "Assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as source:
            branded_source = source.convert("RGBA")
            for filename, size in (
                ("Square44x44Logo.png", 44),
                ("Square150x150Logo.png", 150),
            ):
                asset = ImageOps.fit(branded_source, (size, size), method=Image.Resampling.LANCZOS)
                asset.save(assets_dir / filename, format="PNG", optimize=True)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Invalid branded Store asset source {source_path}: {exc}") from exc


def xml_text(value: str) -> str:
    return escape(value, {"'": "&apos;", '"': "&quot;"})


def write_manifest(
    staging_dir: Path,
    package_name: str,
    publisher: str,
    version: str,
    display_name: str,
    publisher_display_name: str,
) -> None:
    description = "Cli de consulta a SAGE50"
    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:uap5="http://schemas.microsoft.com/appx/manifest/uap/windows10/5"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap uap5">
  <Identity Name={quoteattr(package_name)}
            Publisher={quoteattr(publisher)}
            Version={quoteattr(version)} />
  <Properties>
    <DisplayName>{xml_text(display_name)}</DisplayName>
    <PublisherDisplayName>{xml_text(publisher_display_name)}</PublisherDisplayName>
    <Logo>Assets\\Square150x150Logo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0" />
  </Dependencies>
  <Resources>
    <Resource Language="es-es" />
  </Resources>
  <Applications>
    <Application Id="App" Executable="s50info.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName={quoteattr(display_name)}
                          Description={quoteattr(description)}
                          BackgroundColor="transparent"
                          Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png" />
      <Extensions>
        <uap5:Extension Category="windows.appExecutionAlias"
                          Executable="s50info.exe"
                          EntryPoint="Windows.FullTrustApplication">
          <uap5:AppExecutionAlias>
            <uap5:ExecutionAlias Alias="s50info.exe" />
          </uap5:AppExecutionAlias>
        </uap5:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
'''
    (staging_dir / "AppxManifest.xml").write_text(manifest, encoding="utf-8", newline="\n")


def copy_build_output(build_root: Path, staging_dir: Path) -> None:
    if build_root.is_file():
        if build_root.suffix.lower() != ".exe":
            raise SystemExit(f"PyInstaller output is not an executable: {build_root}")
        shutil.copy2(build_root, staging_dir / "s50info.exe")
        return

    if not build_root.is_dir():
        raise SystemExit(f"PyInstaller output not found: {build_root}")

    exe_path = build_root / "s50info.exe"
    if not exe_path.is_file():
        raise SystemExit(f"Application executable not found: {exe_path}")

    for item in build_root.iterdir():
        target = staging_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def create_staging_directory() -> Path:
    """Create an isolated staging dir outside the repository.

    Staging must never be the repo's msix/ source folder: rmtree-ing it
    would delete tracked files (AppxManifest.xml, Assets/) and any
    uncommitted work on an interrupted build.
    """
    return Path(tempfile.mkdtemp(prefix="s50info_msix_staging_"))


def copy_scripts_folder(scripts_dir: Path, staging_dir: Path) -> None:
    """Copy example scripts so the app can sync them into its state directory.

    `s50info` copies `<exe_dir>/script` into %APPDATA%/s50info on first run;
    the package must ship that folder or the sync silently does nothing.
    """
    if not scripts_dir.is_dir():
        raise SystemExit(f"Scripts folder not found: {scripts_dir}")
    if not any(scripts_dir.iterdir()):
        raise SystemExit(f"Scripts folder is empty: {scripts_dir}")
    shutil.copytree(
        scripts_dir,
        staging_dir / "script",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def run_command(command: list[str], label: str) -> None:
    print(" ".join(command))
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"{label} failed with exit code {exc.returncode}") from exc


def main() -> int:
    args = parse_args()
    root = repo_root()

    version = read_msix_version(root)
    staging_dir = create_staging_directory()
    build_root = resolve_repo_path(root, args.build_root)
    output_dir = resolve_repo_path(root, args.output_dir)
    asset_source = resolve_repo_path(root, args.asset_source)
    scripts_dir = resolve_repo_path(root, args.scripts_dir)
    output_package = output_dir / f"{args.package_name}-{version}.msix"
    makeappx_path = resolve_tool_path(args.makeappx_path, "makeappx.exe")
    signtool_path = resolve_tool_path(args.signtool_path, "signtool.exe")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        copy_build_output(build_root, staging_dir)
        copy_scripts_folder(scripts_dir, staging_dir)
        write_assets(staging_dir, asset_source)
        write_manifest(
            staging_dir=staging_dir,
            package_name=args.package_name,
            publisher=args.publisher,
            version=version,
            display_name=args.display_name,
            publisher_display_name=args.publisher_display_name,
        )

        if output_package.exists():
            output_package.unlink()

        print(f"Building MSIX: {output_package}")
        run_command(
            [
                makeappx_path,
                "pack",
                "/d",
                str(staging_dir),
                "/p",
                str(output_package),
                "/overwrite",
            ],
            "MakeAppx",
        )

        if args.certificate_path:
            certificate_path = resolve_repo_path(root, args.certificate_path)
            if not certificate_path.is_file():
                raise SystemExit(f"Signing certificate not found: {certificate_path}")

            command = [
                signtool_path,
                "sign",
                "/fd",
                "SHA256",
                "/f",
                str(certificate_path),
            ]
            if args.certificate_password:
                command.extend(["/p", args.certificate_password])
            command.append(str(output_package))
            print(f"Signing MSIX with certificate: {certificate_path}")
            run_command(command, "SignTool")
        else:
            print(
                "Warning: MSIX created unsigned. Partner Center normally requires "
                "the Publisher identity and signing setup to match the reserved app identity."
            )

        print(f"MSIX ready: {output_package}")
        return 0
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
