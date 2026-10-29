"""
Automated Tests for Ollama AI Parser & Integration in CrimeSketchAI.

Covers:
- OllamaClient HTTP requests with mocked responses (no running Ollama required)
- Connection errors, timeouts, HTTP 404 (model not found), and HTTP 500 handling
- OllamaRefinementParser with valid JSON, invalid JSON, and missing keys
- Allowlist validation rejecting unknown features, invalid directions, and invalid magnitudes
- Rejection of unsupported domains and explicit model error responses
- RefinementService integration with parser_mode="ai"
- Strict verification that AI mode NEVER silently falls back to rule-based parser on failure
- Integration of AI mode with live Blender state and bilateral asymmetry
- Verification that no mutating commands (e.g. mpfb_set_targets) are ever called
"""

import json
import socket
import urllib.error
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config import Settings, settings
from backend.main import app, refinement_service, state_service
from backend.storage.database import Database
from backend.models.schemas import RefinementRequest, LiveStateResponse, LiveFeatureState
from backend.parser.refinement_parser import ParseError
from backend.parser.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseError
)
from backend.parser.ollama_parser import OllamaRefinementParser
from backend.service.refinement_service import RefinementService
from backend.service.blender_state_service import BlenderStateService


# ==============================================================================
# 1. OllamaClient Unit Tests
# ==============================================================================

class TestOllamaClient:
    def test_chat_success(self):
        sent_requests = []

        def mock_sender(method, url, payload):
            sent_requests.append((method, url, payload))
            return {
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}'
                },
                "done": True
            }

        client = OllamaClient(
            base_url="http://127.0.0.1:11434",
            model="qwen3:4b",
            timeout=10.0,
            http_sender=mock_sender
        )

        res = client.chat(messages=[{"role": "user", "content": "Make the nose wider."}])
        assert len(sent_requests) == 1
        method, url, payload = sent_requests[0]
        assert method == "POST"
        assert url == "http://127.0.0.1:11434/api/chat"
        assert payload["model"] == "qwen3:4b"
        assert payload["format"] == "json"
        assert payload["stream"] is False
        assert "message" in res
        assert "nose_width" in res["message"]["content"]

    def test_chat_connection_refused(self):
        def mock_sender(method, url, payload):
            raise OllamaConnectionError("Cannot connect to Ollama at http://127.0.0.1:11434.")

        client = OllamaClient(http_sender=mock_sender)
        with pytest.raises(OllamaConnectionError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "Cannot connect to Ollama" in str(exc_info.value)

    def test_chat_timeout(self):
        def mock_sender(method, url, payload):
            raise OllamaTimeoutError("Ollama request timed out after 15.0s.")

        client = OllamaClient(http_sender=mock_sender)
        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "timed out after 15.0s" in str(exc_info.value)

    def test_default_timeout_is_180_seconds(self):
        """Verify default timeout is 180.0 seconds matching settings."""
        client = OllamaClient()
        assert client.timeout == 180.0
        assert settings.OLLAMA_TIMEOUT_SECONDS == 180.0

    def test_custom_timeout_override(self):
        """Verify custom timeout explicitly overrides the default."""
        client = OllamaClient(timeout=45.0)
        assert client.timeout == 45.0

    def test_settings_env_var_override(self, monkeypatch):
        """Verify OLLAMA_TIMEOUT_SECONDS environment variable is honored by Settings."""
        monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "240.0")
        custom_settings = Settings()
        assert custom_settings.OLLAMA_TIMEOUT_SECONDS == 240.0

    @patch("urllib.request.urlopen")
    def test_chat_uses_configured_default_timeout_in_urlopen(self, mock_urlopen):
        """Verify actual urllib.request.urlopen receives the default 180.0s timeout."""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = b'{"model": "qwen3:4b", "message": {"content": "{}"}}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = OllamaClient()
        client.chat([{"role": "user", "content": "test"}])

        assert mock_urlopen.call_count == 1
        call_args, call_kwargs = mock_urlopen.call_args
        assert call_kwargs.get("timeout") == 180.0

    @patch("urllib.request.urlopen")
    def test_chat_timeout_at_180s_error_message(self, mock_urlopen):
        """Verify OllamaTimeoutError with default 180s includes clear diagnostic advice."""
        mock_urlopen.side_effect = socket.timeout("timed out")
        client = OllamaClient()

        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "Make cheekbones prominent"}])

        err_text = str(exc_info.value)
        assert "timed out after 180.0s during model inference" in err_text
        assert "http://127.0.0.1:11434" in err_text
        assert "qwen3:4b" in err_text
        assert "Consider increasing OLLAMA_TIMEOUT_SECONDS in your environment" in err_text

    def test_ollama_parser_timeout_forwarding(self):
        """Verify OllamaRefinementParser supports and forwards timeout parameter."""
        parser_default = OllamaRefinementParser()
        assert parser_default.client.timeout == 180.0

        parser_custom = OllamaRefinementParser(timeout=90.0)
        assert parser_custom.client.timeout == 90.0

    def test_chat_model_not_found(self):
        def mock_sender(method, url, payload):
            raise OllamaModelNotFoundError("Ollama model 'qwen3:4b' not found.")

        client = OllamaClient(http_sender=mock_sender)
        with pytest.raises(OllamaModelNotFoundError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "model 'qwen3:4b' not found" in str(exc_info.value)

    def test_check_health(self):
        def mock_sender_ok(method, url, payload):
            return {"models": [{"name": "qwen3:4b"}]}

        client_ok = OllamaClient(http_sender=mock_sender_ok)
        assert client_ok.check_health() is True

        def mock_sender_fail(method, url, payload):
            raise ConnectionError("down")

        client_fail = OllamaClient(http_sender=mock_sender_fail)
        assert client_fail.check_health() is False

    @patch("urllib.request.urlopen")
    def test_chat_urllib_socket_timeout_not_masked_as_connection_error(self, mock_urlopen):
        """Regression test: socket.timeout must raise OllamaTimeoutError, NOT OllamaConnectionError."""
        mock_urlopen.side_effect = socket.timeout("timed out")
        client = OllamaClient(base_url="http://127.0.0.1:11434", timeout=15.0)

        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "Make cheekbones prominent"}])
        assert "timed out after 15.0s during model inference" in str(exc_info.value)
        # Ensure it is NOT misdiagnosed as OllamaConnectionError
        assert not isinstance(exc_info.value, OllamaConnectionError)

    @patch("urllib.request.urlopen")
    def test_chat_urllib_direct_timeout_error_not_masked_as_connection_error(self, mock_urlopen):
        """Regression test: direct TimeoutError must raise OllamaTimeoutError, NOT OllamaConnectionError."""
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = OllamaClient(base_url="http://127.0.0.1:11434", timeout=15.0)

        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "Make cheekbones prominent"}])
        assert "timed out after 15.0s during model inference" in str(exc_info.value)
        assert not isinstance(exc_info.value, OllamaConnectionError)

    @patch("urllib.request.urlopen")
    def test_chat_urllib_url_error_with_timeout_reason(self, mock_urlopen):
        """Regression test: URLError wrapping socket.timeout must raise OllamaTimeoutError."""
        mock_urlopen.side_effect = urllib.error.URLError(socket.timeout("timed out"))
        client = OllamaClient(base_url="http://127.0.0.1:11434", timeout=15.0)

        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "timed out after 15.0s during model inference" in str(exc_info.value)

    @patch("urllib.request.urlopen")
    def test_chat_urllib_url_error_with_connection_refused(self, mock_urlopen):
        """Genuine connection error must raise OllamaConnectionError."""
        mock_urlopen.side_effect = urllib.error.URLError(ConnectionRefusedError("Connection refused"))
        client = OllamaClient(base_url="http://127.0.0.1:11434", timeout=15.0)

        with pytest.raises(OllamaConnectionError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "Cannot connect to Ollama" in str(exc_info.value)

    @patch("urllib.request.urlopen")
    def test_chat_urllib_direct_connection_refused(self, mock_urlopen):
        """Direct ConnectionRefusedError must raise OllamaConnectionError."""
        mock_urlopen.side_effect = ConnectionRefusedError("Connection refused")
        client = OllamaClient(base_url="http://127.0.0.1:11434", timeout=15.0)

        with pytest.raises(OllamaConnectionError) as exc_info:
            client.chat([{"role": "user", "content": "test"}])
        assert "Connection refused" in str(exc_info.value)


# ==============================================================================
# 2. OllamaRefinementParser Unit Tests
# ==============================================================================

class TestOllamaRefinementParser:
    def test_valid_output_mapping(self):
        def mock_sender(method, url, payload):
            user_msg = payload["messages"][-1]["content"]
            if "nose" in user_msg:
                content = '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}'
            elif "eyes" in user_msg:
                content = '{"feature_id": "eye_size", "direction": "decrease", "magnitude": "slight"}'
            elif "chin" in user_msg:
                content = '{"feature_id": "chin_prominence", "direction": "increase", "magnitude": "significant"}'
            else:
                content = '{"feature_id": "mouth_width", "direction": "decrease", "magnitude": "moderate"}'
            return {"message": {"content": content}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        # 1. Nose width
        p1 = parser.parse("Make the nose slightly wider.")
        assert p1.feature_id == "nose_width"
        assert p1.direction == 1
        assert p1.magnitude == 0.05
        assert p1.delta == 0.05
        assert p1.target_identifier == "nose:nose-scale-horiz-decr-incr:unsided"
        assert p1.target_shapekey == "nose-scale-horiz-incr"

        # 2. Eye size decrease
        p2 = parser.parse("Make the eyes smaller.")
        assert p2.feature_id == "eye_size"
        assert p2.direction == -1
        assert p2.magnitude == 0.05
        assert p2.delta == -0.05
        assert p2.is_sided is True
        assert p2.target_shapekey == "l-eye-scale-decr"

        # 3. Chin prominence significant
        p3 = parser.parse("Increase chin prominence significantly.")
        assert p3.feature_id == "chin_prominence"
        assert p3.direction == 1
        assert p3.magnitude == 0.10
        assert p3.delta == 0.10

    def test_invalid_json_handling(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": "I am not returning JSON! Just plain text."}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider.")
        assert "invalid JSON" in str(exc_info.value)

    def test_missing_required_keys(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": '{"feature_id": "nose_width"}'}}  # missing direction and magnitude

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider.")
        assert "missing required field" in str(exc_info.value)

    def test_unsupported_feature_proposed_by_model(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": '{"feature_id": "hair_color", "direction": "increase", "magnitude": "slight"}'}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Adjust hair.")
        assert "unsupported" in str(exc_info.value).lower()

    def test_invalid_direction(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": '{"feature_id": "nose_width", "direction": "sideways", "magnitude": "slight"}'}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider.")
        assert "invalid direction" in str(exc_info.value).lower()

    def test_invalid_magnitude(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": '{"feature_id": "nose_width", "direction": "increase", "magnitude": "extreme"}'}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider.")
        assert "invalid magnitude" in str(exc_info.value).lower()

    def test_model_explicit_error_response(self):
        def mock_sender(method, url, payload):
            return {"message": {"content": '{"error": "Tattoo modifications are not in the allowlist."}'}}

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Add a dragon tattoo on his cheek.")
        assert "rejected request" in str(exc_info.value).lower()
        assert "tattoo modifications are not in the allowlist" in str(exc_info.value).lower()

    def test_embedded_json_in_conversational_response(self):
        """Resilience: extracts JSON even when model wraps output in conversational prose."""
        def mock_sender(method, url, payload):
            return {
                "message": {
                    "content": (
                        "Sure! Here is the JSON interpretation for the witness instruction:\n"
                        '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}\n'
                        "Let me know if you need any adjustments!"
                    )
                }
            }

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("Make the nose wider.")
        assert res.feature_id == "nose_width"
        assert res.direction == 1
        assert res.magnitude == 0.05
        assert res.delta == 0.05

    def test_stringified_float_magnitude(self):
        """Allows valid float string magnitude emitted by neural model."""
        def mock_sender(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "chin_width", "direction": "decrease", "magnitude": "0.08"}'
                }
            }

        client = OllamaClient(http_sender=mock_sender)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("Make the chin narrower.")
        assert res.feature_id == "chin_width"
        assert res.direction == -1
        assert res.magnitude == 0.08
        assert res.delta == -0.08


# ==============================================================================
# 3. RefinementService AI Mode Integration Tests
# ==============================================================================

@pytest.fixture
def temp_db(tmp_path: Path):
    return Database(tmp_path / "test_ollama_refinements.db")


class TestRefinementServiceOllamaIntegration:
    def test_service_ai_mode_success(self, temp_db):
        def mock_sender(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}'
                }
            }

        ai_client = OllamaClient(http_sender=mock_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        service = RefinementService(db=temp_db, ai_parser=ai_parser)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-AI-01",
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.parser_mode == "ai"
        assert res.parser_model == "qwen3:4b"
        assert res.feature_id == "nose_width"
        assert res.proposed_delta == 0.05
        assert res.proposed_value == 0.25

        # Check SQLite audit logging
        logs = temp_db.get_logs(case_id="CASE-AI-01")
        assert len(logs) == 1
        assert logs[0]["status"] == "PREVIEW_READY"
        details = json.loads(logs[0]["details_json"])
        assert details["parser_mode"] == "ai"
        assert details["parser_model"] == "qwen3:4b"

    def test_service_ai_mode_no_silent_fallback_on_connection_error(self, temp_db):
        """CRITICAL: If the user explicitly selects AI mode, failure must NOT silently fall back to rule-based!"""
        def mock_sender(method, url, payload):
            raise OllamaConnectionError("Cannot connect to Ollama at http://127.0.0.1:11434.")

        ai_client = OllamaClient(http_sender=mock_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        service = RefinementService(db=temp_db, ai_parser=ai_parser)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-AI-FAIL-NO-FALLBACK",
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        # Must be REJECTED, not silently succeeded via rule-based parser!
        assert res.status == "REJECTED"
        assert res.parser_mode == "ai"
        assert "Cannot connect to Ollama" in res.error_message
        assert res.proposed_payload is None

        # Confirm rejection is audited in SQLite
        logs = temp_db.get_logs(case_id="CASE-AI-FAIL-NO-FALLBACK")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        assert "Cannot connect to Ollama" in logs[0]["error_message"]

    def test_service_ai_mode_no_silent_fallback_on_timeout(self, temp_db):
        def mock_sender(method, url, payload):
            raise OllamaTimeoutError("Ollama request timed out after 15.0s.")

        ai_client = OllamaClient(http_sender=mock_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        service = RefinementService(db=temp_db, ai_parser=ai_parser)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-AI-TIMEOUT",
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "timed out after 15.0s" in res.error_message

    def test_service_ai_mode_timeout_at_180s_reports_helpful_error(self, temp_db):
        """Test service reporting 180.0s timeout diagnosis when model exceeds inference limit."""
        def mock_sender(method, url, payload):
            raise OllamaTimeoutError(
                "Ollama request to http://127.0.0.1:11434 timed out after 180.0s during model inference. "
                "The model 'qwen3:4b' may need more time to complete reasoning. "
                "Consider increasing OLLAMA_TIMEOUT_SECONDS in your environment."
            )

        ai_client = OllamaClient(http_sender=mock_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        service = RefinementService(db=temp_db, ai_parser=ai_parser)

        req = RefinementRequest(
            text="Make the jaw wider and more square.",
            case_id="CASE-AI-TIMEOUT-180",
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "timed out after 180.0s during model inference" in res.error_message
        assert "Consider increasing OLLAMA_TIMEOUT_SECONDS" in res.error_message
        assert "qwen3:4b" in res.error_message

        # Verify audit log recorded rejection
        logs = temp_db.get_logs(case_id="CASE-AI-TIMEOUT-180")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        assert "timed out after 180.0s" in logs[0]["error_message"]

    def test_service_ai_mode_with_live_blender_state(self, temp_db):
        """Test AI parser interpreting command with live Blender target values."""
        def mock_ai_sender(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}'
                }
            }

        def mock_blender_sender(cmd, params):
            return {
                "status": "ok",
                "result": {
                    "found": True,
                    "modifiers": [
                        {"section": "nose", "category": "nose-scale-horiz-decr-incr", "side": "unsided", "value": 0.40}
                    ]
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        state_srv = BlenderStateService(command_sender=mock_blender_sender)
        service = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=state_srv)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True,
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.parser_mode == "ai"
        assert res.value_source == "live_blender"
        assert res.is_live_blender_value is True
        assert res.current_value == 0.40
        assert res.proposed_value == 0.45

    def test_service_ai_mode_bilateral_asymmetry_preserved(self, temp_db):
        """Test AI parser with bilateral asymmetric cheekbones in live Blender mode."""
        def mock_ai_sender(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "cheekbone_prominence", "direction": "increase", "magnitude": "slight"}'
                }
            }

        def mock_blender_sender(cmd, params):
            return {
                "status": "ok",
                "result": {
                    "found": True,
                    "modifiers": [
                        {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "left", "value": 0.10},
                        {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "right", "value": 0.25}
                    ]
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        state_srv = BlenderStateService(command_sender=mock_blender_sender)
        service = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=state_srv)

        req = RefinementRequest(
            text="Make the cheekbones more prominent.",
            use_live_state=True,
            parser_mode="ai"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.parser_mode == "ai"
        assert res.is_symmetric is False
        assert res.left_current_value == 0.10
        assert res.right_current_value == 0.25
        assert res.left_proposed_value == 0.15
        assert res.right_proposed_value == 0.30
        assert round(res.right_proposed_value - res.left_proposed_value, 4) == 0.15

    def test_service_default_parser_mode_remains_rule_based(self, temp_db):
        """When parser_mode is omitted, default is rule_based without touching Ollama."""
        called_ai = []

        def tracking_ai_sender(method, url, payload):
            called_ai.append(url)
            return {}

        ai_client = OllamaClient(http_sender=tracking_ai_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        service = RefinementService(db=temp_db, ai_parser=ai_parser)

        req = RefinementRequest(text="Make the nose slightly wider.")
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.parser_mode == "rule_based"
        assert len(called_ai) == 0  # AI client was never called

    def test_no_mutation_tool_is_called_with_ai(self, temp_db):
        """Verify that running in AI mode never invokes mutation tools."""
        dispatched_bridge = []

        def tracking_bridge(cmd, params):
            dispatched_bridge.append(cmd)
            return {"status": "ok", "result": {"found": True, "modifiers": []}}

        def mock_ai_sender(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}'
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai_sender)
        ai_parser = OllamaRefinementParser(client=ai_client)
        state_srv = BlenderStateService(command_sender=tracking_bridge)
        service = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=state_srv)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True,
            parser_mode="ai"
        )
        res = service.process_dry_run(req)
        assert res.status == "PREVIEW_READY"

        for forbidden in ["set_targets", "set_macro_details", "set_face_units"]:
            assert forbidden not in dispatched_bridge


# ==============================================================================
# 4. FastAPI Integration Tests with AI Mode
# ==============================================================================

class TestApiOllamaIntegration:
    def test_api_refine_with_ai_mode(self, monkeypatch, tmp_path):
        client = TestClient(app)
        test_db = Database(tmp_path / "api_ai_test.db")
        refinement_service.db = test_db

        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": '{"feature_id": "eye_size", "direction": "increase", "magnitude": "slight"}'
                }
            }

        monkeypatch.setattr(refinement_service.ai_parser.client, "_http_sender", mock_ai)

        resp = client.post("/refine", json={
            "text": "Make the eyes slightly larger.",
            "parser_mode": "ai",
            "case_id": "CASE-API-AI"
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "PREVIEW_READY"
        assert data["parser_mode"] == "ai"
        assert data["parser_model"] == "qwen3:4b"
        assert data["feature_id"] == "eye_size"
        assert data["proposed_delta"] == 0.05

    def test_api_health_includes_ollama_metadata(self, monkeypatch):
        client = TestClient(app)

        def mock_tags(method, url, payload):
            return {"models": [{"name": "qwen3:4b"}]}

        monkeypatch.setattr(refinement_service.ai_parser.client, "_http_sender", mock_tags)

        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["parser_mode"] == "rule_based"
        assert data["ollama_model"] == "qwen3:4b"
        assert data["ollama_available"] is True

    def test_multi_feature_witness_description_parsing(self):
        """Verify parsing a 5-feature witness description via Ollama response."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "cheekbone_prominence", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "chin_width", "direction": "decrease", "magnitude": "slight"},
                            {"feature_id": "eye_size", "direction": "decrease", "magnitude": "slight"},
                            {"feature_id": "head_width", "direction": "decrease", "magnitude": "slight"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        parsed = parser.parse("A person with a broad nose, prominent cheekbones, a slightly pointed chin, small eyes, and a narrow face.")
        assert parsed.feature_id == "multi_feature"
        assert hasattr(parsed, "features") and len(parsed.features) == 5

        fids = [f.feature_id for f in parsed.features]
        assert fids == ["nose_width", "cheekbone_prominence", "chin_width", "eye_size", "head_width"]
        assert parsed.features[0].direction == 1
        assert parsed.features[0].delta == 0.05
        assert parsed.features[2].direction == -1
        assert parsed.features[2].delta == -0.05

    def test_multi_feature_duplicate_instruction_rejection(self):
        """Duplicate adjustments for the same feature in the same batch are rejected."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "significant"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider and broader.")
        assert "duplicate adjustments" in str(exc_info.value).lower()
        assert "nose width" in str(exc_info.value).lower()

    def test_multi_feature_conflicting_instruction_rejection(self):
        """Conflicting adjustments for the same feature in the same batch are rejected."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "nose_width", "direction": "decrease", "magnitude": "slight"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("Make the nose wider but also narrower.")
        assert "conflicting adjustments" in str(exc_info.value).lower()
        assert "nose width" in str(exc_info.value).lower()

    def test_multi_feature_unsupported_domain_prefilter_rejection(self):
        """Witness description containing unsupported attributes (e.g. hair color) is rejected upfront."""
        def mock_ai(method, url, payload):
            return {"message": {"content": '{"features": []}'}}

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError) as exc_info:
            parser.parse("A person with a broad nose and long blonde hair.")
        assert "hair" in str(exc_info.value).lower()

    def test_ai_parsing_expanded_controls(self):
        """AI parser accurately maps newly added Phase 1 controls."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nasal_bridge_hump", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "jaw_width", "direction": "increase", "magnitude": "moderate"},
                            {"feature_id": "ear_protrusion", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "mouth_upperlip_volume", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "hooded_eyelids", "direction": "increase", "magnitude": "slight"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("A suspect with a dorsal hump, wide jaw, protruding ears, plump upper lip, and hooded eyes.")
        assert len(res.features) == 5
        fids = [f.feature_id for f in res.features]
        assert fids == ["nasal_bridge_hump", "jaw_width", "ear_protrusion", "mouth_upperlip_volume", "hooded_eyelids"]
        assert res.features[1].magnitude == 0.08  # moderate -> 0.08
        assert res.features[2].is_sided is True  # ear_protrusion is bilateral
        assert res.features[2].target_shapekey == "l-ear-wing-incr"
        assert res.features[4].target_shapekey == "l-eye-eyefold-convex"

    def test_ai_parsing_pure_hairstyle(self):
        """AI parser maps hairstyle swap request."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [],
                        "assets": [{"asset_type": "hair", "asset_id": "bob01"}]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("Change the hairstyle to a bob cut.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        assert res.asset_adjustments[0].asset_id == "bob01"
        assert res.asset_adjustments[0].fragment == "bob01/bob01.mhclo"
        assert res.asset_adjustments[0].action == "swap"

    def test_ai_parsing_bald_and_eyebrows(self):
        """AI parser maps bald and eyebrow adjustments."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [],
                        "assets": [
                            {"asset_type": "hair", "asset_id": "bald"},
                            {"asset_type": "eyebrows", "asset_id": "eyebrow010"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("Make the suspect bald with thick eyebrows.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].asset_id == "bald"
        assert types["hair"].fragment is None
        assert types["hair"].action == "remove"
        assert types["eyebrows"].asset_id == "eyebrow010"
        assert types["eyebrows"].fragment == "eyebrow010/eyebrow010.mhclo"

    def test_ai_parsing_combined_assets_and_geometry(self):
        """AI parser maps simultaneous hair, eyebrow, and geometry controls."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "jaw_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "cheekbone_prominence", "direction": "increase", "magnitude": "slight"}
                        ],
                        "assets": [
                            {"asset_type": "hair", "asset_id": "afro01"},
                            {"asset_type": "eyebrows", "asset_id": "eyebrow006"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        res = parser.parse("A person with an afro, thin curved eyebrows, a wide jaw, and prominent cheekbones.")
        assert res.feature_id == "multi_feature"
        assert len(res.features) == 2
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].asset_id == "afro01"
        assert types["eyebrows"].asset_id == "eyebrow006"

    def test_ai_parsing_invalid_asset_id_rejected(self):
        """AI parser rejects unsupported asset proposed by model."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [],
                        "assets": [{"asset_type": "hair", "asset_id": "rainbow_hair"}]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError, match="unsupported hairstyle 'rainbow_hair'"):
            parser.parse("Change hairstyle to rainbow.")

    def test_ai_parsing_conflicting_assets_rejected(self):
        """AI parser rejects conflicting asset instructions."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [],
                        "assets": [
                            {"asset_type": "hair", "asset_id": "afro01"},
                            {"asset_type": "hair", "asset_id": "bob01"}
                        ]
                    })
                }
            }

        client = OllamaClient(http_sender=mock_ai)
        parser = OllamaRefinementParser(client=client)

        with pytest.raises(ParseError, match="Conflicting or duplicate asset instructions"):
            parser.parse("Give him an afro and a bob cut.")


