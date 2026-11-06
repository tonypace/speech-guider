"""Exercise dev-process ownership without starting servers or desktop apps."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def dev_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "bin").mkdir()
    (project / "speech-guider" / "bin").mkdir(parents=True)
    shutil.copy(Path(__file__).resolve().parents[1] / "scripts" / "dev.sh", project / "scripts")
    return project


def executable(path: Path, code: str) -> None:
    path.write_text(f"#!{sys.executable}\n" + code)
    path.chmod(0o755)


def run_dev(project: Path, mode: str) -> subprocess.CompletedProcess[str]:
    executable(
        project / "speech-guider" / "bin" / "python",
        """import os, signal, subprocess, sys, time
from pathlib import Path
root = Path.cwd()
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
(root / "child_pid").write_text(str(child.pid))
def stop(*args):
    child.wait(timeout=5)
    (root / "backend_stopped").touch()
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
(root / "backend_ready").touch()
if os.environ["DEV_TEST_MODE"] == "late_death":
    while not (root / "desktop_started").exists(): time.sleep(0.01)
    sys.exit(1)
while True: time.sleep(0.1)
""",
    )
    executable(
        project / "bin" / "curl",
        """import os, sys
from pathlib import Path
sys.exit(0 if Path("backend_ready").exists() and os.environ["DEV_TEST_MODE"] != "unhealthy" else 1)
""",
    )
    executable(
        project / "bin" / "npm",
        """import os, signal, sys, time
from pathlib import Path
Path("desktop_started").touch()
def stop(*args):
    Path("desktop_stopped").touch()
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
if os.environ["DEV_TEST_MODE"] == "success":
    time.sleep(0.1)
    sys.exit(0)
while True: time.sleep(0.1)
""",
    )
    # Accelerate readiness polling, preserving enough time for fake processes to start.
    executable(project / "bin" / "sleep", "import time\ntime.sleep(0.05)\n")
    env = dict(os.environ, PATH=f"{project / 'bin'}:{os.environ['PATH']}", DEV_TEST_MODE=mode)
    return subprocess.run(
        ["bash", str(project / "scripts" / "dev.sh")],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_desktop_exit_cleans_backend_and_descendant(dev_project: Path) -> None:
    result = run_dev(dev_project, "success")
    assert result.returncode == 0, result.stderr
    assert (dev_project / "backend_stopped").exists()
    child_pid = int((dev_project / "child_pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_failed_health_never_launches_desktop(dev_project: Path) -> None:
    result = run_dev(dev_project, "unhealthy")
    assert result.returncode == 1
    assert not (dev_project / "desktop_started").exists()
    assert (dev_project / "backend_stopped").exists()


def test_late_backend_death_stops_desktop(dev_project: Path) -> None:
    result = run_dev(dev_project, "late_death")
    assert result.returncode == 1
    assert "FastAPI exited while desktop" in result.stderr
    assert (dev_project / "desktop_stopped").exists()
