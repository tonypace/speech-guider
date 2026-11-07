"""Build an offline, local noncommercial macOS installer from verified assets."""

import argparse
import hashlib
import html
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src-tauri/target/release/bundle/macos/Speech Guider.app"
OUTPUT = ROOT / "build/installer/Speech Guider - Local Noncommercial.pkg"
R4_FILES = (
    "configs/nine_channel_v12_100ms.yaml",
    "weights/r4.pt",
    "weights/contentvec/config.json",
    "weights/contentvec/preprocessor_config.json",
    "weights/contentvec/model.safetensors",
)
GGML_LIBRARIES = (
    "libggml.0.dylib",
    "libggml-base.0.dylib",
    "libggml-cpu.0.dylib",
    "libggml-blas.0.dylib",
    "libggml-metal.0.dylib",
)
OMNIVOICE_HASHES = {
    "omnivoice-base-Q8_0.gguf": "2882d887921798aea13d45236556bdf8012842ab6f8cd2690943eead6289f298",
    "omnivoice-tokenizer-F32.gguf": "83820c6316da023076af7c1d06de5e38dcd09ae9f42203675bf8b3bd9a58e330",
}


def _run(*args: str | Path, capture: bool = False) -> str:
    return subprocess.run(args, check=True, capture_output=capture, text=True).stdout or ""


def _sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _copy(source: Path, target: Path, digest: str | None = None) -> None:
    if digest and _sha256(source) != digest:
        raise ValueError(f"Asset checksum mismatch: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _stage_r4(source: Path, target: Path) -> None:
    hashes = {}
    for line in (source / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        hashes[name.removeprefix("*").removeprefix("./")] = digest
    for name in R4_FILES:
        _copy(source / name, target / name, hashes[name])
    for name in ("LICENSE", "SOURCE_COMMIT", "CONTENTVEC_STATE_SHA256"):
        _copy(source / name, target / name)
    _copy(ROOT / "docs/third-party/contentvec/LICENSE.txt", target / "ContentVec-LICENSE.txt")


def _relocate_binary(path: Path, dependencies: tuple[str, ...]) -> None:
    if _run("lipo", "-archs", path, capture=True).strip() != "arm64":
        raise ValueError(f"Expected arm64 executable or library: {path}")
    linked = _run("otool", "-L", path, capture=True).splitlines()[1:]
    for line in linked:
        name = line.strip().split(" (", 1)[0]
        if name.startswith(("/usr/lib/", "/System/Library/")):
            continue
        if name not in {f"@rpath/{item}" for item in dependencies}:
            raise ValueError(f"Nonportable OmniVoice dependency {name!r} in {path.name}")
    commands = _run("otool", "-l", path, capture=True)
    rpaths = re.findall(r"cmd LC_RPATH\s+cmdsize \d+\s+path (.+?) \(offset \d+\)", commands)
    edits: list[str | Path] = []
    for rpath in rpaths:
        if rpath != "@loader_path":
            edits.extend(("-delete_rpath", rpath))
    if "@loader_path" not in rpaths and path.suffix != ".dylib":
        edits.extend(("-add_rpath", "@loader_path"))
    if edits:
        _run("install_name_tool", *edits, path)
    _run("codesign", "--force", "--sign", "-", path)


def _stage_omnivoice(source: Path, target: Path) -> None:
    for name in ("omnivoice-tts", *GGML_LIBRARIES):
        binary = (source / "build" / name).resolve(strict=True)
        if not binary.is_relative_to((source / "build").resolve()):
            raise ValueError(f"OmniVoice build file points outside its build directory: {binary}")
        _copy(binary, target / name)
        _relocate_binary(target / name, GGML_LIBRARIES)
    for name, digest in OMNIVOICE_HASHES.items():
        _copy(source / "models" / name, target / "models" / name, digest)
    for relative, name in (
        ("LICENSE", "OmniVoice.cpp-LICENSE.txt"),
        ("ggml/LICENSE", "GGML-LICENSE.txt"),
        ("vendor/cpp-httplib/LICENSE", "cpp-httplib-LICENSE.txt"),
    ):
        _copy(source / relative, target / "licenses" / name)
    _copy(ROOT / "docs/r4-LICENSE.txt", target / "licenses/OmniVoice-weights-CC-BY-NC-4.0.txt")
    for notice in (ROOT / "docs/third-party/omnivoice").iterdir():
        _copy(notice, target / "licenses" / notice.name)
    _copy(ROOT / "docs/third-party/omnivoice/NOTICE.txt", target / "NOTICE.txt")
    revision = _run("git", "-C", source, "rev-parse", "HEAD", capture=True).strip()
    (target / "SOURCE_CHECKOUT").write_text(
        f"https://github.com/ServeurpersoCom/omnivoice.cpp\n{revision}\n", encoding="utf-8"
    )
    # Confirm the executable loads the relocated libraries without the source directory on PATH.
    subprocess.run(
        (target / "omnivoice-tts", "--help"),
        check=True,
        cwd=target,
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
    )


def _make_product(app: Path, work: Path, output: Path, attributions: str) -> None:
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    components = work / "components.plist"
    components.write_bytes(
        plistlib.dumps(
            [
                {
                    "RootRelativeBundlePath": app.name,
                    "BundleIsRelocatable": False,
                    "BundleIsVersionChecked": True,
                    "BundleHasStrictIdentifier": True,
                    "BundleOverwriteAction": "upgrade",
                }
            ]
        )
    )
    package = work / "SpeechGuider.pkg"
    _run(
        "pkgbuild",
        "--root",
        app.parent,
        "--component-plist",
        components,
        "--install-location",
        "/Applications",
        "--identifier",
        f"{info['CFBundleIdentifier']}.installer",
        "--version",
        info["CFBundleShortVersionString"],
        package,
    )
    requirements = work / "requirements.plist"
    requirements.write_bytes(
        plistlib.dumps({"arch": ["arm64"], "os": [info["LSMinimumSystemVersion"]]})
    )
    distribution = work / "Distribution.xml"
    _run(
        "productbuild",
        "--synthesize",
        "--product",
        requirements,
        "--package",
        package,
        distribution,
    )
    tree = ET.parse(distribution)
    root = tree.getroot()
    title = root.find("title")
    if title is None:
        title = ET.Element("title")
        root.insert(0, title)
    title.text = "Speech Guider (Local Noncommercial)"
    root.insert(1, ET.Element("readme", {"file": "ReadMe.html", "mime-type": "text/html"}))
    tree.write(distribution, encoding="utf-8", xml_declaration=True)
    resources = work / "resources"
    resources.mkdir()
    (resources / "ReadMe.html").write_text(
        f"<html><body><pre style='white-space:pre-wrap'>{html.escape(attributions)}</pre></body></html>",
        encoding="utf-8",
    )
    temp_output = work / "Product.pkg"
    _run(
        "productbuild",
        "--distribution",
        distribution,
        "--package-path",
        work,
        "--resources",
        resources,
        temp_output,
    )
    temp_output.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=APP)
    parser.add_argument("--r4", type=Path, default=ROOT / "external/R4 26-11-06")
    parser.add_argument("--omnivoice", type=Path, default=ROOT / "omnivoice-tts")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        parser.error("Use an Apple Silicon Mac.")
    app, output = args.app.resolve(strict=True), args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _run("codesign", "--verify", "--deep", "--strict", app)
    with tempfile.TemporaryDirectory(prefix="installer-", dir=output.parent) as directory:
        work = Path(directory)
        payload = work / "payload"
        payload.mkdir()
        staged = payload / "Speech Guider.app"
        _run("ditto", app, staged)
        assets = staged / "Contents/Resources/assets"
        assets.mkdir()
        _stage_r4(args.r4.resolve(strict=True), assets / "r4")
        _stage_omnivoice(args.omnivoice.resolve(strict=True), assets / "omnivoice")
        installer_credits = (ROOT / "docs/installer-assets.md").read_text(encoding="utf-8")
        r4_credits = (ROOT / "docs/attribution-for-r4.md").read_text(encoding="utf-8")
        attributions = f"{installer_credits.rstrip()}\n\n{r4_credits}"
        (assets / "ATTRIBUTIONS.md").write_text(attributions, encoding="utf-8")
        manifest = "\n".join(
            f"{_sha256(p)}  {p.relative_to(assets)}"
            for p in sorted(assets.rglob("*"))
            if p.is_file()
        )
        (assets / "SHA256SUMS").write_text(manifest + "\n", encoding="utf-8")
        _run(
            "codesign",
            "--force",
            "--sign",
            "-",
            "--entitlements",
            ROOT / "src-tauri/Entitlements.plist",
            staged,
        )
        _run("codesign", "--verify", "--deep", "--strict", staged)
        _make_product(staged, work, output, attributions)
    print(f"Local noncommercial installer: {output}")


if __name__ == "__main__":
    main()
