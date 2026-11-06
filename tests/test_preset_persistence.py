"""Preset persistence recovery, atomicity, and concurrency coverage."""

import json
import threading
from pathlib import Path

import pytest

from app.services import state


@pytest.fixture
def preset_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "presets.json"
    monkeypatch.setattr(state, "PRESETS_FILE", path)
    return path


def test_load_recovers_malformed_top_level_shape(preset_file: Path) -> None:
    preset_file.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    loaded = state.load_presets()

    assert "i" in loaded
    assert loaded["i"]["name"] == "beat"


def test_load_skips_invalid_entries_and_nonfinite_params(preset_file: Path) -> None:
    preset_file.write_text(
        json.dumps(
            {
                "i": {"name": "broken", "params": {"lip_aperture": float("nan")}},
                "u": {"name": "good", "params": {"lip_aperture": 0.25}},
                "bad": None,
            }
        ),
        encoding="utf-8",
    )

    loaded = state.load_presets()

    assert loaded["i"]["name"] == "beat"
    assert loaded["u"]["name"] == "good"
    assert loaded["u"]["params"]["lip_aperture"] == pytest.approx(0.25)
    assert "bad" not in loaded


def test_interrupted_atomic_write_keeps_previous_file(
    preset_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = '{"previous": {"name": "safe", "params": {}}}'
    preset_file.write_text(original, encoding="utf-8")

    def interrupt_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(state.os, "replace", interrupt_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        state.save_presets({"new": {"name": "next", "params": {}}})

    assert preset_file.read_text(encoding="utf-8") == original
    assert list(preset_file.parent.glob(".presets.json.*.tmp")) == []


def test_concurrent_saves_preserve_all_read_modify_write_updates(
    preset_file: Path,
) -> None:
    thread_count = 12
    barrier = threading.Barrier(thread_count)
    failures: list[BaseException] = []

    def save(index: int) -> None:
        try:
            barrier.wait()
            state.save_preset(f"x{index}", {"name": f"custom-{index}", "params": {}})
        except BaseException as exc:  # surfaced in the test thread
            failures.append(exc)

    threads = [threading.Thread(target=save, args=(index,)) for index in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    loaded = state.load_presets()
    assert all(loaded[f"x{index}"]["name"] == f"custom-{index}" for index in range(thread_count))


def test_default_preset_path_is_project_root_based() -> None:
    assert state.PRESETS_FILE.is_absolute()
    assert state.PRESETS_FILE == state.PROJECT_ROOT / "presets.json"


def test_save_rejects_nonfinite_before_normalization(preset_file: Path) -> None:
    with pytest.raises(ValueError, match="finite"):
        state.save_preset("i", {"name": "bad", "params": {"lip_aperture": float("nan")}})
    assert not preset_file.exists()
