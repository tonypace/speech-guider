"""Freeze the native arm64 Python backend for the macOS Tauri bundle."""

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / "build"
PACKAGER_DIR = BUILD_DIR / "desktop-packager"
WORK_DIR = BUILD_DIR / "desktop-backend-work"
DIST_DIR = BUILD_DIR / "desktop-backend"
EXECUTABLE_NAME = "speech-guider-backend"


def build() -> None:
    """Package the interpreter, imports, and rendered web app inputs."""
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("Build with native arm64 Python on an Apple Silicon Mac.")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use the project's Python 3.12 environment for release builds.")

    if not PACKAGER_DIR.is_dir() and importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "Install build tools: python -m pip install --target build/desktop-packager "
            "-r requirements-desktop-build.txt"
        )

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    # Keep caches and isolated tools in the build tree; never require a user's home directory.
    env["PYINSTALLER_CONFIG_DIR"] = str(WORK_DIR / "cache")
    env.pop("PYTHONPATH", None)
    if PACKAGER_DIR.is_dir():
        env["PYTHONPATH"] = str(PACKAGER_DIR)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--target-arch",
        "arm64",
        "--name",
        EXECUTABLE_NAME,
        "--paths",
        str(PROJECT_ROOT),
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR / "analysis"),
        "--specpath",
        str(WORK_DIR),
        "--add-data",
        f"{PROJECT_ROOT / 'app' / 'templates'}:app/templates",
        "--add-data",
        f"{PROJECT_ROOT / 'static'}:static",
        # CLTS dependencies read the language registry and CLDF ontology on import.
        "--collect-data",
        "language_tags",
        "--collect-data",
        "pycldf",
        "--collect-data",
        "pyclts",
        # Uvicorn and Transformers resolve these modules dynamically at runtime.
        "--collect-submodules",
        "uvicorn",
        "--collect-submodules",
        "transformers.models.auto",
        "--collect-submodules",
        "transformers.models.hubert",
        "--collect-submodules",
        "transformers.models.wav2vec2",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "IPython",
        str(PROJECT_ROOT / "app" / "desktop_backend.py"),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)

    executable = DIST_DIR / EXECUTABLE_NAME / EXECUTABLE_NAME
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SystemExit(f"Expected executable missing after packaging: {executable}")
    print(f"Frozen desktop backend: {executable}")


if __name__ == "__main__":
    build()
