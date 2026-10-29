"""
Tests for Live-State-Aware Dry-Run Refinement in CrimeSketchAI.

Covers:
- Live nose-width preview using a mocked current value different from cached baseline
- Failed live read that must strictly reject without falling back to cached reference
- Bilateral targets with asymmetric left/right values preserving side differences
- Bilateral independent clamping when one side reaches boundary
- Missing or malformed live target data handling
- Boundary clamping for live values
- Backward compatibility when use_live_state=False
- Caller-supplied current_value rejection in live mode
- Strict audit verification that no mutating command (e.g. mpfb_set_targets) is ever called
- FastAPI HTTP integration tests for POST /refine with use_live_state=True
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app, state_service, refinement_service
from backend.storage.database import Database
from backend.service.refinement_service import RefinementService
from backend.service.blender_state_service import BlenderStateService
from backend.models.schemas import RefinementRequest, LiveStateResponse, LiveFeatureState
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST


def make_mock_live_state(feature_overrides=None, blender_available=True, source="live_blender", error_details=None):
    """Helper to generate a mock LiveStateResponse."""
    features = {}
    
    # Defaults matching allowlist
    default_vals = {
        fid: (
            fdef.reference_value,
            fdef.is_sided,
            (fdef.reference_value if fdef.is_sided else None),
            (fdef.reference_value if fdef.is_sided else None)
        )
        for fid, fdef in VERIFIED_ALLOWLIST.items()
    }
    # Keep historical test baseline where nose_width is 0.35
    default_vals["nose_width"] = (0.35, False, None, None)

    if feature_overrides:
        default_vals.update(feature_overrides)

    for fid, (val, sided, l_val, r_val) in default_vals.items():
        if val is None:
            continue
        features[fid] = LiveFeatureState(
            feature_id=fid,
            display_name=fid.replace("_", " "),
            section="test_sec",
            category=f"{fid}-cat",
            is_sided=sided,
            side="left,right" if sided else "unsided",
            value=val,
            left_value=l_val,
            right_value=r_val,
            is_symmetric=(l_val == r_val) if sided else None,
            target_identifiers=[f"test_sec:{fid}-cat:{'unsided' if not sided else 'left'}"]
        )

    return LiveStateResponse(
        blender_available=blender_available,
        character_name="Human",
        source=source,
        timestamp_utc="2026-10-28T12:00:00Z",
        features=features if blender_available and source == "live_blender" else None,
        error_details=error_details
    )


class MockBlenderStateService(BlenderStateService):
    def __init__(self, response_generator=None):
        super().__init__()
        self.response_generator = response_generator or (lambda char: make_mock_live_state())
        self.recorded_calls = []

    def get_live_state(self, character_name=None, timeout=None):
        self.recorded_calls.append(("get_live_state", character_name, timeout))
        return self.response_generator(character_name)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "live_refine_test.db"
    return Database(db_file)


class TestLiveStateRefinement:
    def test_live_nose_width_differs_from_cached_baseline(self, temp_db):
        """Mocked live nose-width is 0.35 (cached reference is 0.20). Proposed delta +0.05 -> proposed 0.40."""
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({"nose_width": (0.35, False, None, None)})
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-LIVE-01",
            character_name="Human",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.mode == "dry_run"
        assert res.feature_id == "nose_width"

        # Explicit live Blender source assertions
        assert res.value_source == "live_blender"
        assert res.is_live_blender_value is True
        assert res.current_value == 0.35
        assert res.reference_value == 0.35
        assert res.proposed_delta == 0.05
        assert res.proposed_value == 0.40
        assert res.is_boundary_clamped is False
        assert "Data source: live Blender target stack" in res.message

        # Payload modifiers check
        assert res.proposed_payload is not None
        assert res.proposed_payload.modifiers[0].value == 0.40
        assert res.proposed_payload.modifiers[0].side == "unsided"

        # Verify SQLite audit trail
        logs = temp_db.get_logs(case_id="CASE-LIVE-01")
        assert len(logs) == 1
        assert logs[0]["status"] == "PREVIEW_READY"
        assert logs[0]["current_value"] == 0.35
        assert logs[0]["proposed_value"] == 0.40
        assert "live_blender" in logs[0]["details_json"]

    def test_failed_live_read_never_falls_back_to_cached(self, temp_db):
        """When Blender is unavailable, preview must be rejected. Cached values must NOT be substituted."""
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state(
                blender_available=False,
                source="unavailable",
                error_details="Socket connection refused: Blender not running"
            )
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-FAIL-LIVE",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert res.value_source == "unavailable"
        assert res.is_live_blender_value is False
        assert res.proposed_payload is None
        assert "Live Blender state unavailable" in res.error_message
        assert "Socket connection refused" in res.error_message

        # Verify rejection logged to SQLite
        logs = temp_db.get_logs(case_id="CASE-FAIL-LIVE")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        assert "Socket connection refused" in logs[0]["error_message"]

    def test_bilateral_asymmetric_targets_preserve_difference(self, temp_db):
        """
        Bilateral feature (cheekbone_prominence) with asymmetric initial values:
        Left = 0.10, Right = 0.25 (Difference = 0.15).
        Instruction: 'Make the cheekbones more prominent.' (Delta = +0.05)
        Expected: Left = 0.15, Right = 0.30 (Difference = 0.15 is preserved).
        """
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({
                "cheekbone_prominence": (0.10, True, 0.10, 0.25)
            })
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the cheekbones more prominent.",
            case_id="CASE-ASYM-CHEEK",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.feature_id == "cheekbone_prominence"
        assert res.is_symmetric is False
        assert res.left_current_value == 0.10
        assert res.right_current_value == 0.25
        assert res.left_proposed_value == 0.15
        assert res.right_proposed_value == 0.30
        assert round(res.right_proposed_value - res.left_proposed_value, 4) == 0.15
        assert "Preserved bilateral asymmetry" in res.message

        # Verify modifiers list in proposed payload has distinct left and right values
        mods = {m.side: m.value for m in res.proposed_payload.modifiers}
        assert mods["left"] == 0.15
        assert mods["right"] == 0.30

    def test_bilateral_independent_boundary_clamping(self, temp_db):
        """
        Bilateral feature where one side reaches the +1.0 boundary while other side doesn't:
        Left = 0.98, Right = 0.80.
        Instruction: 'Make the eyes larger.' (Delta = +0.05).
        Expected: Left clamped to 1.0, Right adjusted to 0.85.
        """
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({
                "eye_size": (0.98, True, 0.98, 0.80)
            })
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the eyes larger.",
            case_id="CASE-CLAMP-BILATERAL",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.is_boundary_clamped is True
        assert res.left_proposed_value == 1.0
        assert res.right_proposed_value == 0.85
        assert "Left proposed adjustment reaches slider limit" in res.boundary_warning
        assert "Right proposed adjustment" not in res.boundary_warning

        mods = {m.side: m.value for m in res.proposed_payload.modifiers}
        assert mods["left"] == 1.0
        assert mods["right"] == 0.85

    def test_missing_target_in_live_data(self, temp_db):
        """When requested feature is missing from the live Blender stack, request is rejected."""
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({
                "nose_width": (None, False, None, None)  # Omit nose_width from features
            })
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "target state missing for feature" in res.error_message

    def test_unsided_live_boundary_clamping(self, temp_db):
        """Unsided live forehead size at 0.98 clamped to 1.0."""
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({
                "forehead_size": (0.98, False, None, None)
            })
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the forehead taller.",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.is_boundary_clamped is True
        assert res.proposed_value == 1.0
        assert "reaches the maximum slider limit" in res.boundary_warning

    def test_backward_compatibility_when_use_live_state_false(self, temp_db):
        """When use_live_state=False, retains cached reference values regardless of live Blender state."""
        mock_service = MockBlenderStateService(
            response_generator=lambda char: make_mock_live_state({
                "nose_width": (0.75, False, None, None)
            })
        )
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=False
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.value_source == "cached_reference"
        assert res.is_live_blender_value is False
        # Uses catalog reference 0.20, NOT 0.75
        assert res.reference_value == 0.20
        assert res.proposed_value == 0.25
        assert len(mock_service.recorded_calls) == 0  # BlenderStateService was never called!

    def test_caller_supplied_current_value_rejected_in_live_mode(self, temp_db):
        """Supplying current_value with use_live_state=True is still strictly forbidden and rejected."""
        mock_service = MockBlenderStateService()
        service = RefinementService(db=temp_db, state_service=mock_service)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True,
            current_value=0.55
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "Caller-supplied 'current_value' is rejected" in res.error_message
        assert len(mock_service.recorded_calls) == 0

    def test_verification_no_mutation_tool_is_called(self, temp_db):
        """Verify that live refinement never sends any mutation commands to Blender."""
        dispatched_bridge_commands = []

        def spy_sender(cmd, params):
            dispatched_bridge_commands.append(cmd)
            return {
                "status": "ok",
                "result": {
                    "found": True,
                    "modifiers": [
                        {"section": "nose", "category": "nose-scale-horiz-decr-incr", "side": "unsided", "value": 0.20}
                    ]
                }
            }

        state_srv = BlenderStateService(command_sender=spy_sender)
        service = RefinementService(db=temp_db, state_service=state_srv)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        # Only 'get_target_stack' should have been invoked
        assert dispatched_bridge_commands == ["get_target_stack"]

        forbidden_tools = {
            "set_targets",
            "set_macro_details",
            "set_face_units",
            "apply_expressions",
            "symmetrize_targets",
            "create_human"
        }
        for cmd in dispatched_bridge_commands:
            assert cmd not in forbidden_tools


class TestApiLiveRefinement:
    def test_api_refine_with_live_state_success(self, monkeypatch, tmp_path):
        client = TestClient(app)
        test_db = Database(tmp_path / "api_live_test.db")
        refinement_service.db = test_db

        def mock_sender(cmd, params):
            return {
                "status": "ok",
                "result": {
                    "found": True,
                    "modifiers": [
                        {"section": "nose", "category": "nose-scale-horiz-decr-incr", "side": "unsided", "value": 0.40}
                    ]
                }
            }

        monkeypatch.setattr(state_service, "_command_sender", mock_sender)

        resp = client.post("/refine", json={
            "text": "Make the nose slightly wider.",
            "use_live_state": True,
            "case_id": "CASE-API-LIVE"
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "PREVIEW_READY"
        assert data["value_source"] == "live_blender"
        assert data["is_live_blender_value"] is True
        assert data["current_value"] == 0.40
        assert data["proposed_value"] == 0.45
        assert data["proposed_payload"]["modifiers"][0]["value"] == 0.45

        # Check SQLite audit record
        logs = test_db.get_logs(case_id="CASE-API-LIVE")
        assert len(logs) == 1
        assert logs[0]["current_value"] == 0.40
        assert logs[0]["proposed_value"] == 0.45

    def test_api_refine_with_live_state_blender_unavailable(self, monkeypatch, tmp_path):
        client = TestClient(app)
        test_db = Database(tmp_path / "api_live_fail.db")
        refinement_service.db = test_db

        def mock_sender(cmd, params):
            raise ConnectionError("MPFB Bridge port 9877 unreachable")

        monkeypatch.setattr(state_service, "_command_sender", mock_sender)

        resp = client.post("/refine", json={
            "text": "Make the nose slightly wider.",
            "use_live_state": True,
            "case_id": "CASE-API-FAIL"
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "REJECTED"
        assert data["value_source"] == "unavailable"
        assert data["is_live_blender_value"] is False
        assert "Live Blender state unavailable" in data["error_message"]
        assert data["proposed_payload"] is None

        # Verify logged rejection
        logs = test_db.get_logs(case_id="CASE-API-FAIL")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"

