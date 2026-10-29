"""
Automated tests for CrimeSketchAI Blender Live State Service & GET /state endpoint.

Covers:
- Successful live reads with extraction of the 10 allowlisted features
- Handling of missing/pruned targets and asymmetries
- Malformed MCP response envelopes
- Unavailable Blender (ConnectionError)
- Timeout handling (hanging connection)
- Strict verification that no mutation tool is ever invoked
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app, state_service
from backend.service.blender_state_service import BlenderStateService
from backend.models.schemas import LiveStateResponse

# Sample valid MPFB response envelope matching real Blender bridge output
SAMPLE_VALID_STACK_RESPONSE = {
    "status": "ok",
    "protocol_version": 2,
    "command": "get_target_stack",
    "result": {
        "found": True,
        "subject_name": "Human",
        "subject_resolved_by": "name",
        "basemesh_name": "Human",
        "has_shapekeys": True,
        "modifier_count": 18,
        "asymmetries": [],
        "counts_by_kind": {
            "macro": 8,
            "detail": 18
        },
        "modifiers": [
            {"section": "nose", "category": "nose-scale-horiz-decr-incr", "side": "unsided", "value": 0.20},
            {"section": "nose", "category": "nose-scale-vert-decr-incr", "side": "unsided", "value": 0.05},
            {"section": "chin", "category": "chin-width-decr-incr", "side": "unsided", "value": -0.10},
            {"section": "chin", "category": "chin-prominent-decr-incr", "side": "unsided", "value": 0.10},
            {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "left", "value": 0.15},
            {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "right", "value": 0.15},
            {"section": "eyes", "category": "eye-scale-decr-incr", "side": "left", "value": 0.10},
            {"section": "eyes", "category": "eye-scale-decr-incr", "side": "right", "value": 0.10},
            {"section": "head", "category": "head-scale-horiz-decr-incr", "side": "unsided", "value": -0.15},
            {"section": "head", "category": "head-scale-vert-decr-incr", "side": "unsided", "value": 0.10},
            {"section": "mouth", "category": "mouth-scale-horiz-decr-incr", "side": "unsided", "value": -0.05}
            # forehead-scale-vert-decr-incr omitted to simulate neutral/pruned 0.0 value
        ]
    }
}


class TestBlenderStateService:
    def test_successful_live_read(self):
        calls = []

        def mock_sender(cmd, params):
            calls.append((cmd, params))
            return SAMPLE_VALID_STACK_RESPONSE

        service = BlenderStateService(command_sender=mock_sender)
        res: LiveStateResponse = service.get_live_state("Human")

        assert res.blender_available is True
        assert res.source == "live_blender"
        assert res.character_name == "Human"
        assert res.error_details is None
        assert res.features is not None
        assert len(res.features) == 38

        # Unsided features
        assert res.features["nose_width"].value == 0.20
        assert res.features["nose_height"].value == 0.05
        assert res.features["chin_width"].value == -0.10
        assert res.features["chin_prominence"].value == 0.10
        assert res.features["head_width"].value == -0.15
        assert res.features["head_height"].value == 0.10
        assert res.features["mouth_width"].value == -0.05

        # Bilateral features
        cheek = res.features["cheekbone_prominence"]
        assert cheek.is_sided is True
        assert cheek.value == 0.15
        assert cheek.left_value == 0.15
        assert cheek.right_value == 0.15
        assert cheek.is_symmetric is True

        eyes = res.features["eye_size"]
        assert eyes.is_sided is True
        assert eyes.value == 0.10
        assert eyes.left_value == 0.10
        assert eyes.right_value == 0.10
        assert eyes.is_symmetric is True

        # Verify command sent
        assert len(calls) == 1
        assert calls[0][0] == "get_target_stack"
        assert calls[0][1]["name"] == "Human"
        assert calls[0][1]["include_macro"] is True

    def test_missing_targets_and_asymmetries(self):
        # forehead was omitted in sample response, should default to 0.0
        def mock_sender(cmd, params):
            resp = {
                "status": "ok",
                "result": {
                    "found": True,
                    "modifiers": [
                        {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "left", "value": 0.20},
                        {"section": "cheek", "category": "cheek-bones-decr-incr", "side": "right", "value": 0.10}
                    ]
                }
            }
            return resp

        service = BlenderStateService(command_sender=mock_sender)
        res = service.get_live_state("Human")

        assert res.blender_available is True
        assert res.source == "live_blender"
        assert res.features["forehead_size"].value == 0.0
        assert res.features["nose_width"].value == 0.0

        cheek = res.features["cheekbone_prominence"]
        assert cheek.left_value == 0.20
        assert cheek.right_value == 0.10
        assert cheek.is_symmetric is False

    def test_character_not_found(self):
        def mock_sender(cmd, params):
            return {
                "status": "ok",
                "result": {
                    "found": False,
                    "message": "Subject 'MissingHuman' not found"
                }
            }

        service = BlenderStateService(command_sender=mock_sender)
        res = service.get_live_state("MissingHuman")

        assert res.blender_available is True
        assert res.source == "unavailable"
        assert res.features is None
        assert "not found in the active Blender scene" in res.error_details

    def test_malformed_mcp_responses(self):
        # Case 1: Status not ok
        def mock_sender_err(cmd, params):
            return {"status": "error", "message": "Internal Blender error"}

        service = BlenderStateService(command_sender=mock_sender_err)
        res = service.get_live_state("Human")
        assert res.source == "unavailable"
        assert res.features is None
        assert "non-ok status" in res.error_details

        # Case 2: Missing result dict
        def mock_sender_no_res(cmd, params):
            return {"status": "ok"}

        service = BlenderStateService(command_sender=mock_sender_no_res)
        res = service.get_live_state("Human")
        assert res.source == "unavailable"
        assert res.features is None
        assert "result' key is missing" in res.error_details

        # Case 3: Modifiers not a list
        def mock_sender_bad_mod(cmd, params):
            return {"status": "ok", "result": {"found": True, "modifiers": "bad_type"}}

        service = BlenderStateService(command_sender=mock_sender_bad_mod)
        res = service.get_live_state("Human")
        assert res.source == "unavailable"
        assert res.features is None
        assert "modifiers' key is not a list" in res.error_details

    def test_unavailable_blender_connection_refused(self):
        def mock_sender(cmd, params):
            raise ConnectionError("Cannot connect to MPFB Bridge at 127.0.0.1:9877: Connection refused")

        service = BlenderStateService(command_sender=mock_sender)
        res = service.get_live_state("Human")

        assert res.blender_available is False
        assert res.source == "unavailable"
        assert res.features is None
        assert "Cannot connect to MPFB Bridge" in res.error_details

    def test_blender_timeout(self):
        def mock_hanging_sender(cmd, params):
            time.sleep(1.0)  # Sleep longer than the 0.2s timeout
            return SAMPLE_VALID_STACK_RESPONSE

        service = BlenderStateService(command_sender=mock_hanging_sender, default_timeout=0.2)
        start = time.time()
        res = service.get_live_state("Human")
        duration = time.time() - start

        assert duration < 0.8
        assert res.blender_available is False
        assert res.source == "unavailable"
        assert res.features is None
        assert "timed out after 0.2s" in res.error_details

    def test_confirmation_no_mutation_tool_is_invoked(self):
        """Strict verification: Only get_target_stack is ever called; NO mutation tools."""
        dispatched_commands = []

        def tracking_sender(cmd, params):
            dispatched_commands.append(cmd)
            return SAMPLE_VALID_STACK_RESPONSE

        service = BlenderStateService(command_sender=tracking_sender)
        service.get_live_state("Human")

        assert len(dispatched_commands) == 1
        assert dispatched_commands[0] == "get_target_stack"

        # Explicitly confirm NO mutation tools were invoked
        forbidden_tools = {
            "set_targets",
            "set_macro_details",
            "set_face_units",
            "apply_expressions",
            "symmetrize_targets",
            "create_human",
            "refit_human",
            "add_rig",
            "add_asset",
            "save_preset",
            "save_expression"
        }
        for cmd in dispatched_commands:
            assert cmd not in forbidden_tools


class TestApiStateEndpoint:
    def test_get_state_success(self, monkeypatch):
        client = TestClient(app)

        def mock_sender(cmd, params):
            return SAMPLE_VALID_STACK_RESPONSE

        monkeypatch.setattr(state_service, "_command_sender", mock_sender)

        resp = client.get("/state?character_name=Human")
        assert resp.status_code == 200
        data = resp.json()

        assert data["blender_available"] is True
        assert data["source"] == "live_blender"
        assert data["character_name"] == "Human"
        assert data["features"]["nose_width"]["value"] == 0.20
        assert data["features"]["eye_size"]["value"] == 0.10
        assert data["error_details"] is None

    def test_get_state_unavailable_blender(self, monkeypatch):
        client = TestClient(app)

        def mock_sender(cmd, params):
            raise ConnectionError("Connection refused by target machine")

        monkeypatch.setattr(state_service, "_command_sender", mock_sender)

        resp = client.get("/state")
        assert resp.status_code == 200
        data = resp.json()

        assert data["blender_available"] is False
        assert data["source"] == "unavailable"
        assert data["features"] is None
        assert "Cannot connect to MPFB Bridge" in data["error_details"]

