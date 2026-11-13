"""Installed assets must remain readable after pkgbuild changes ownership to root."""

from pathlib import Path

import pytest

from scripts.build_desktop_installer import _copy


@pytest.mark.parametrize("executable, expected_mode", [(False, 0o644), (True, 0o755)])
def test_owner_only_source_becomes_accessible(
    tmp_path: Path, executable: bool, expected_mode: int
) -> None:
    source = tmp_path / "private-source"
    source.write_bytes(b"model fixture")
    source.chmod(0o700)
    target = tmp_path / "payload" / "asset"
    _copy(source, target, executable=executable)
    assert target.stat().st_mode & 0o777 == expected_mode
    assert target.read_bytes() == source.read_bytes()
    assert source.stat().st_mode & 0o777 == 0o700
