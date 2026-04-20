"""Regression tests for errors endpoint fallback behavior and payload handling."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestSelectErrorAAIPayloadHandling:
    """Tests for _resolve_animation_params AAI payload error handling."""

    def test_invalid_error_index_raises_400(self):
        """Invalid error index should return 400 Bad Request."""
        response = client.post(
            "/api/select-error",
            json={
                "error_index": 99,
                "errors": [
                    {
                        "target_phoneme": "/t/",
                        "predicted_phoneme": "/d/",
                        "word_context": "test",
                    }
                ],
            },
        )
        assert response.status_code == 400
        assert "Invalid error index" in response.json()["detail"]

    def test_negative_error_index_raises_400(self):
        """Negative error index should return 400 Bad Request."""
        response = client.post(
            "/api/select-error",
            json={
                "error_index": -1,
                "errors": [
                    {
                        "target_phoneme": "/t/",
                        "predicted_phoneme": "/d/",
                        "word_context": "test",
                    }
                ],
            },
        )
        assert response.status_code == 400

    def test_malformed_aai_payload_uses_fallback(self):
        """Malformed AAI payload should fall back to symbolic mapping."""
        from app.api.errors import AAIPayloadError, _resolve_animation_params

        # Create a mock mapper
        mapper = MagicMock()
        mapper.get_animation_params.return_value = {"lip_aperture": 0.5}

        # Malformed payload (missing required keys)
        malformed_payload = {"invalid_key": "value"}

        with pytest.raises(AAIPayloadError) as exc_info:
            _resolve_animation_params("/t/", {"lip_aperture": 0.5}, malformed_payload, mapper)

        assert "Invalid AAI payload" in str(exc_info.value)

    def test_valid_aai_payload_parses_correctly(self):
        """Valid AAI payload should be parsed successfully."""
        from app.api.errors import _resolve_animation_params

        # Create a mock mapper
        mapper = MagicMock()
        mapper.get_animation_params.return_value = {"lip_aperture": 0.5}

        # Valid payload
        valid_payload = {
            "source_dataset": "xrmb",
            "normalization": "z_score",
            "values": [0.0] * 9,
        }

        # This should not raise an error and should return parsed result
        with patch("app.api.errors.parse_aai_animation_payload") as mock_parse:
            mock_parse.return_value = {"lip_aperture": 0.75}
            result = _resolve_animation_params("/t/", {"lip_aperture": 0.5}, valid_payload, mapper)
            assert result == {"lip_aperture": 0.75}
            mock_parse.assert_called_once()

    def test_non_dict_aai_payload_uses_symbolic_fallback(self):
        """Non-dict AAI payload should use symbolic mapping."""
        from app.api.errors import _resolve_animation_params

        # Create a mock mapper
        mapper = MagicMock()
        mapper.get_animation_params.return_value = {"lip_aperture": 0.5}

        # Non-dict payload (None)
        result = _resolve_animation_params("/t/", {"lip_aperture": 0.5}, None, mapper)

        # Should use symbolic mapping
        mapper.get_animation_params.assert_called_once_with("/t/")
        assert result == {"lip_aperture": 0.5}


class TestSelectErrorEndpointFallback:
    """Tests for select_error endpoint fallback behavior."""

    @patch("app.api.errors.ArticulatoryMapper")
    def test_aai_payload_error_uses_default_params(self, mock_mapper_class):
        """AAI payload error should fall back to default articulatory state."""
        response = client.post(
            "/api/select-error",
            json={
                "error_index": 0,
                "errors": [
                    {
                        "target_phoneme": "/t/",
                        "predicted_phoneme": "/d/",
                        "word_context": "test",
                        "animation_right": {"invalid": "payload"},
                    }
                ],
            },
        )

        # Should succeed with fallback parameters
        assert response.status_code == 200
        data = response.json()
        assert "animation_params" in data
        assert "left" in data["animation_params"]
        assert "right" in data["animation_params"]

    @patch("app.api.errors.ArticulatoryMapper")
    def test_mapper_data_error_uses_default_params(self, mock_mapper_class):
        """Mapper data error should fall back to default articulatory state."""
        mock_mapper = MagicMock()
        mock_mapper.get_animation_params.side_effect = KeyError("Unknown phoneme")
        mock_mapper_class.return_value = mock_mapper

        response = client.post(
            "/api/select-error",
            json={
                "error_index": 0,
                "errors": [
                    {
                        "target_phoneme": "/unknown/",
                        "predicted_phoneme": "/also_unknown/",
                        "word_context": "test",
                    }
                ],
            },
        )

        # Should succeed with fallback parameters
        assert response.status_code == 200
        data = response.json()
        assert "animation_params" in data


class TestExceptionTypeHierarchy:
    """Tests for custom exception types."""

    def test_aai_payload_error_is_exception(self):
        """AAIPayloadError should inherit from Exception."""
        from app.api.errors import AAIPayloadError

        assert issubclass(AAIPayloadError, Exception)

    def test_aai_payload_error_preserves_cause(self):
        """AAIPayloadError should preserve the original exception cause."""
        from app.api.errors import AAIPayloadError

        original = KeyError("Missing key: values")
        try:
            raise AAIPayloadError("Failed to parse") from original
        except AAIPayloadError as e:
            assert e.__cause__ is original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
