"""Tests for rendered settings payload, PUT /api/settings persistence, and recovery."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import settings as settings_api
from app.main import app
from app.services import state


@pytest.fixture(autouse=True)
def isolate_settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(state, "DATA_DIR", tmp_path)
    return tmp_path / "settings.json"


def _extract_rendered_settings(html: str) -> dict[str, Any]:
    match = re.search(r"window\.__SPEECH_GUIDER_SETTINGS__\s*=\s*(\{.*?\});", html)
    assert match is not None, "Expected embedded __SPEECH_GUIDER_SETTINGS__ payload in HTML"
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def test_root_renders_default_settings_and_contact_availability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "r4"
    bundle.mkdir(parents=True)
    monkeypatch.setenv("SSL_AAI_BUNDLE_PATH", str(bundle))

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert _extract_rendered_settings(response.text) == {
            "contact_enabled": True,
            "lip_enabled": True,
            "calibrate_enabled": True,
            "labiodental_enabled": True,
            "dental_enabled": False,
            "silence_mode": "reviewed",
            "microphone_enabled": True,
            "microphone_device_id": "",
            "microphone_label": "",
            "remote_enabled": True,
            "remote_record_mode": "toggle",
            "remote_bindings": {
                "record": "",
                "play_pause": "",
                "speed_up": "",
                "speed_down": "",
            },
            "contact_available": False,
            "lip_available": False,
            "calibrate_available": False,
            "labiodental_available": False,
            "dental_available": False,
            "silence_available": False,
        }
        assert "Contact weights are missing." in response.text

        contact_weights = bundle / "weights" / "contact.pt"
        contact_weights.parent.mkdir(parents=True, exist_ok=True)
        contact_weights.write_bytes(b"weights")

        with_contact = client.get("/")
        assert with_contact.status_code == 200
        assert _extract_rendered_settings(with_contact.text)["contact_available"] is True


def test_put_settings_persists_to_disk_and_renders_on_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "r4"
    (bundle / "weights").mkdir(parents=True)
    (bundle / "weights" / "contact.pt").write_bytes(b"weights")
    monkeypatch.setenv("SSL_AAI_BUNDLE_PATH", str(bundle))

    requested = {
        "contact_enabled": False,
        "lip_enabled": False,
        "calibrate_enabled": True,
        "labiodental_enabled": False,
        "dental_enabled": True,
        "silence_mode": "expanded",
        "microphone_enabled": False,
        "microphone_device_id": "usb-mic-01",
        "microphone_label": "Studio USB Mic",
        "remote_enabled": True,
        "remote_record_mode": "hold",
        "remote_bindings": {
            "record": "PageDown",
            "play_pause": "PageUp",
            "speed_up": "AudioVolumeUp",
            "speed_down": "AudioVolumeDown",
        },
    }
    expected_availability = {
        "contact_available": True,
        "lip_available": False,
        "calibrate_available": False,
        "labiodental_available": False,
        "dental_available": False,
        "silence_available": False,
    }

    with TestClient(app) as client:
        put_response = client.put("/api/settings", json=requested)
        assert put_response.status_code == 200
        assert put_response.json() == {**requested, **expected_availability}

        persisted_path = tmp_path / "settings.json"
        assert persisted_path.is_file()
        assert json.loads(persisted_path.read_text(encoding="utf-8")) == requested

        home_response = client.get("/")
        assert home_response.status_code == 200
        assert _extract_rendered_settings(home_response.text) == {
            **requested,
            **expected_availability,
        }


@pytest.mark.parametrize("field", ["microphone_device_id", "microphone_label"])
def test_put_settings_rejects_oversized_strings_with_422(tmp_path: Path, field: str) -> None:
    payload = {
        "contact_enabled": True,
        "microphone_enabled": True,
        "microphone_device_id": "mic-1",
        "microphone_label": "Mic 1",
        field: "x" * 513,
    }

    with TestClient(app) as client:
        response = client.put("/api/settings", json=payload)

    assert response.status_code == 422
    assert not (tmp_path / "settings.json").exists()


def test_put_settings_accepts_max_length_and_reports_write_errors() -> None:
    valid_payload = {
        "contact_enabled": True,
        "microphone_enabled": True,
        "microphone_device_id": "d" * 512,
        "microphone_label": "l" * 512,
    }

    with TestClient(app) as client:
        ok_response = client.put("/api/settings", json=valid_payload)
        assert ok_response.status_code == 200

        with patch("app.api.settings._write_settings", side_effect=OSError("disk full")):
            err_response = client.put("/api/settings", json=valid_payload)
        assert err_response.status_code == 500
        assert err_response.json()["detail"] == "Could not save settings."


@pytest.mark.parametrize(
    "corrupt_content",
    [
        "{not valid json",
        json.dumps({"microphone_label": "x" * 513}),
        json.dumps({"contact_enabled": ["bad-type"]}),
    ],
)
def test_recovers_from_malformed_or_invalid_settings_json(
    tmp_path: Path, corrupt_content: str
) -> None:
    (tmp_path / "settings.json").write_text(corrupt_content, encoding="utf-8")

    loaded = settings_api.load_settings()
    assert loaded == settings_api.AppSettings()

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        rendered = _extract_rendered_settings(response.text)
        assert rendered["contact_enabled"] is True
        assert rendered["microphone_enabled"] is True
        assert rendered["microphone_device_id"] == ""
        assert rendered["microphone_label"] == ""


def test_recovers_from_unreadable_settings_file(tmp_path: Path) -> None:
    # A directory at settings.json raises IsADirectoryError (OSError) on read_bytes()
    # reliably regardless of filesystem/user permissions.
    (tmp_path / "settings.json").mkdir()

    loaded = settings_api.load_settings()
    assert loaded == settings_api.AppSettings()

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        rendered = _extract_rendered_settings(response.text)
        assert rendered["microphone_device_id"] == ""


def test_loads_legacy_settings_json_without_remote_fields(tmp_path: Path) -> None:
    legacy = {
        "contact_enabled": False,
        "microphone_enabled": True,
        "microphone_device_id": "mic-1",
        "microphone_label": "Legacy Mic",
    }
    (tmp_path / "settings.json").write_text(json.dumps(legacy), encoding="utf-8")

    loaded = settings_api.load_settings()
    assert loaded.contact_enabled is False
    assert loaded.remote_enabled is True
    assert loaded.remote_record_mode == "toggle"
    assert loaded.remote_bindings == settings_api.RemoteBindings()


def test_put_settings_rejects_invalid_remote_mode_or_oversized_binding() -> None:
    with TestClient(app) as client:
        bad_mode = client.put("/api/settings", json={"remote_record_mode": "double_tap"})
        assert bad_mode.status_code == 422

        bad_key = client.put(
            "/api/settings",
            json={"remote_bindings": {"record": "x" * 65}},
        )
        assert bad_key.status_code == 422
