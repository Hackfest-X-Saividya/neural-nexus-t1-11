"""
Tests for Live Blender Mutation and Application in CrimeSketchAI (POST /apply).

Covers:
1. Successful unsided feature application (nose_width) with verified read-back.
2. Successful bilateral feature application (cheekbones) preserving asymmetric sides.
3. Rejection when confirm_apply is False.
4. Rejection when character_name is not "Human".
5. Rejection when preview_log_id does not exist.
6. Rejection when preview has status other than PREVIEW_READY.
7. Rejection when preview was generated in offline cached-reference mode (use_live_state=False).
8. State drift abortion when target feature value has changed in Blender since preview.
9. State drift abortion when an unrelated allowlisted feature has changed in Blender since preview.
10. Handling when MPFB Bridge returns an error status.
11. Handling when MPFB Bridge reports performed=False.
12. Handling when MPFB Bridge communication times out.
13. Post-mutation read-back failure when target feature values do not match expected within 0.001.
14. Post-mutation read-back failure when an unrelated allowlisted feature was modified.
15. Atomic replay protection preventing duplicate or concurrent application of the same preview.
16. FastAPI integration test for POST /apply with TestClient.
17. FastAPI integration test rejecting duplicate application via TestClient.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app, state_service as main_state_service, mutation_service as main_mutation_service
from backend.models.schemas import (
    RefinementRequest,
    RefinementApplyRequest,
    LiveStateResponse,
    LiveFeatureState,
    EquippedAssetInfo
)
from backend.service.blender_mutation_service import BlenderMutationService
from backend.service.blender_state_service import BlenderStateService
from backend.service.refinement_service import RefinementService
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST
from backend.parser.ollama_client import OllamaClient
from backend.parser.ollama_parser import OllamaRefinementParser
from backend.storage.database import Database


def make_mock_live_state(
    feature_overrides=None,
    blender_available=True,
    source="live_blender",
    error_details=None,
    equipped_hair=None,
    equipped_eyebrows=None,
    custom_assets=False
):
    """Helper to generate a mock LiveStateResponse for all allowlisted features."""
    features = {}
    default_vals = {
        fid: (
            fdef.reference_value,
            fdef.is_sided,
            (fdef.reference_value if fdef.is_sided else None),
            (fdef.reference_value if fdef.is_sided else None)
        )
        for fid, fdef in VERIFIED_ALLOWLIST.items()
    }
    # Keep historical asymmetric test baseline for cheekbones
    default_vals["cheekbone_prominence"] = (0.15, True, 0.15, 0.20)

    if feature_overrides:
        default_vals.update(feature_overrides)

    for fid, (val, sided, l_val, r_val) in default_vals.items():
        if val is None:
            continue
        sec = "macro_head" if "head" in fid or "forehead" in fid else "head"
        features[fid] = LiveFeatureState(
            feature_id=fid,
            display_name=fid.replace("_", " "),
            section=sec,
            category=f"{fid}-cat",
            is_sided=sided,
            side="left,right" if sided else "unsided",
            value=val,
            left_value=l_val,
            right_value=r_val,
            is_symmetric=(l_val == r_val) if sided else None,
            target_identifiers=[f"{sec}:{fid}-cat:{'unsided' if not sided else 'left'}"]
        )

    if not custom_assets:
        if equipped_hair is None:
            equipped_hair = EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01",
                in_current_scene=True
            )
        if equipped_eyebrows is None:
            equipped_eyebrows = EquippedAssetInfo(
                name="Human.eyebrow003",
                object_type="Eyebrows",
                asset_source="eyebrow003/eyebrow003.mhclo",
                asset_id="eyebrow003",
                in_current_scene=True
            )

    return LiveStateResponse(
        blender_available=blender_available,
        character_name="Human",
        source=source,
        timestamp_utc="2026-10-28T12:00:00Z",
        features=features if blender_available and source == "live_blender" else None,
        equipped_hair=equipped_hair,
        equipped_eyebrows=equipped_eyebrows,
        error_details=error_details
    )


class SequenceStateService(BlenderStateService):
    """Mock state service that yields states in sequence (e.g. preview, pre-mutation, post-mutation)."""
    def __init__(self, states):
        super().__init__()
        self.states = list(states)
        self.index = 0
        self.calls = []

    def get_live_state(self, character_name="Human", timeout=None, include_assets=False, **kwargs):
        self.calls.append((character_name, include_assets))
        if self.index < len(self.states):
            state = self.states[self.index]
            self.index += 1
            return state
        return self.states[-1]


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "apply_test.db"
    return Database(db_file)


class TestBlenderMutationSafetyAndExecution:

    def test_apply_success_unsided(self, temp_db):
        """Verify successful application of an unsided feature with read-back verification."""
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_live_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        post_live_state = make_mock_live_state({"nose_width": (0.25, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_live_state, post_live_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        # 1. Generate live dry-run preview
        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True,
            case_id="CASE-001"
        )
        preview = refine_service.process_dry_run(req)
        assert preview.status == "PREVIEW_READY"
        assert preview.proposed_value == 0.25
        preview_id = preview.log_id

        # 2. Mock bridge command sender
        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            return {
                "status": "ok",
                "result": {
                    "performed": True,
                    "changes": [{"category": "nose-width", "target": "head/nose-width-increase", "value": 0.25}]
                }
            }

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        # 3. Apply preview
        apply_req = RefinementApplyRequest(
            preview_log_id=preview_id,
            case_id="CASE-001",
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.drift_checked is True
        assert resp.applied_value == 0.25
        assert resp.previous_value == 0.20
        assert resp.error_message is None

        # Verify command sent to bridge
        assert len(bridge_calls) == 1
        cmd, params = bridge_calls[0]
        assert cmd == "set_targets"
        assert params["name"] == "Human"
        assert params["symmetry"] is False
        assert params["prune"] is True
        assert params["refit"] is False
        assert len(params["modifiers"]) == 1
        assert params["modifiers"][0]["category"] == "nose-scale-horiz-decr-incr"
        assert params["modifiers"][0]["value"] == 0.25
        assert params["modifiers"][0]["side"] == "unsided"

        # Verify database records
        applied_rec = temp_db.get_applied_record(preview_id)
        assert applied_rec is not None
        assert applied_rec["status"] == "APPLIED"
        assert applied_rec["apply_log_id"] == resp.apply_log_id

        log_rec = temp_db.get_log_by_id(resp.apply_log_id)
        assert log_rec["mode"] == "live_apply"
        assert log_rec["status"] == "APPLIED"

    def test_apply_success_bilateral(self, temp_db):
        """Verify successful application of a bilateral asymmetric feature preserving sides."""
        # Baseline: cheekbones left=0.15, right=0.20
        # Increase slightly (+0.05) -> proposed left=0.20, right=0.25
        initial_state = make_mock_live_state({"cheekbone_prominence": (0.15, True, 0.15, 0.20)})
        pre_state = make_mock_live_state({"cheekbone_prominence": (0.15, True, 0.15, 0.20)})
        post_state = make_mock_live_state({"cheekbone_prominence": (0.20, True, 0.20, 0.25)})

        mock_state = SequenceStateService([initial_state, pre_state, post_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        req = RefinementRequest(
            text="Make cheekbones slightly more prominent.",
            use_live_state=True,
            case_id="CASE-002"
        )
        preview = refine_service.process_dry_run(req)
        assert preview.status == "PREVIEW_READY"
        assert preview.left_proposed_value == 0.20
        assert preview.right_proposed_value == 0.25

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        apply_req = RefinementApplyRequest(
            preview_log_id=preview.log_id,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.left_previous_value == 0.15
        assert resp.right_previous_value == 0.20
        assert resp.left_applied_value == 0.20
        assert resp.right_applied_value == 0.25

        # Check bridge params
        cmd, params = bridge_calls[0]
        assert len(params["modifiers"]) == 2
        mods = {m["side"]: m["value"] for m in params["modifiers"]}
        assert mods["left"] == 0.20
        assert mods["right"] == 0.25

    def test_apply_missing_or_false_confirmation(self, temp_db):
        """Reject apply when confirm_apply is False."""
        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(db=temp_db, command_sender=mock_sender)

        apply_req = RefinementApplyRequest(
            preview_log_id=1,
            character_name="Human",
            confirm_apply=False
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "confirm_apply: true" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_invalid_character_name(self, temp_db):
        """Reject apply when character_name is not 'Human'."""
        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(db=temp_db, command_sender=mock_sender)

        apply_req = RefinementApplyRequest(
            preview_log_id=1,
            character_name="Cube",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "must be exactly 'Human'" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_missing_preview_id(self, temp_db):
        """Reject apply when preview_log_id is not in SQLite."""
        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(db=temp_db, command_sender=mock_sender)

        apply_req = RefinementApplyRequest(
            preview_log_id=99999,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "not found" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_rejected_preview_cannot_be_applied(self, temp_db):
        """Reject apply when preview status is REJECTED instead of PREVIEW_READY."""
        # Insert a REJECTED record
        log_id = temp_db.log_request(
            request_text="Make hair longer",
            mode="dry_run",
            status="REJECTED",
            error_message="Feature not supported"
        )

        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(db=temp_db, command_sender=mock_sender)

        apply_req = RefinementApplyRequest(
            preview_log_id=log_id,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "PREVIEW_READY" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_cached_preview_fails_safely(self, temp_db):
        """Reject apply when preview was created in offline cached reference mode."""
        refine_service = RefinementService(db=temp_db)
        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=False  # Offline cached reference
        )
        preview = refine_service.process_dry_run(req)
        assert preview.status == "PREVIEW_READY"
        assert preview.value_source == "cached_reference"

        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(db=temp_db, command_sender=mock_sender)

        apply_req = RefinementApplyRequest(
            preview_log_id=preview.log_id,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "offline cached-reference mode" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_state_drift_target_feature_aborts(self, temp_db):
        """Abort apply if live target feature drifted between preview and apply."""
        preview_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        # Blender state drifted to 0.35 before apply!
        drifted_pre_state = make_mock_live_state({"nose_width": (0.35, False, None, None)})

        mock_state = SequenceStateService([preview_state, drifted_pre_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        )
        preview = refine_service.process_dry_run(req)
        assert preview.status == "PREVIEW_READY"

        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        apply_req = RefinementApplyRequest(
            preview_log_id=preview.log_id,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "State drift detected" in resp.error_message
        assert resp.drift_checked is True
        assert resp.verified is False
        mock_sender.assert_not_called()

    def test_apply_state_drift_unrelated_feature_aborts(self, temp_db):
        """Abort apply if an unrelated allowlisted feature drifted between preview and apply."""
        preview_state = make_mock_live_state({
            "nose_width": (0.20, False, None, None),
            "chin_width": (-0.10, False, None, None)
        })
        # nose_width didn't drift, but chin_width drifted to 0.40!
        drifted_pre_state = make_mock_live_state({
            "nose_width": (0.20, False, None, None),
            "chin_width": (0.40, False, None, None)
        })

        mock_state = SequenceStateService([preview_state, drifted_pre_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        req = RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        )
        preview = refine_service.process_dry_run(req)

        mock_sender = MagicMock()
        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        apply_req = RefinementApplyRequest(
            preview_log_id=preview.log_id,
            character_name="Human",
            confirm_apply=True
        )
        resp = mutation_svc.apply_refinement(apply_req)

        assert resp.status == "APPLY_FAILED"
        assert "State drift detected on unrelated feature" in resp.error_message
        mock_sender.assert_not_called()

    def test_apply_bridge_error_status(self, temp_db):
        """Handle error status from MPFB bridge gracefully."""
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        def mock_error_sender(cmd, params):
            return {"status": "error", "message": "Blender internal script execution error"}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_error_sender
        )

        resp = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "MPFB Bridge returned error status" in resp.error_message
        assert resp.verified is False

    def test_apply_bridge_not_performed(self, temp_db):
        """Handle bridge response where performed=False."""
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        def mock_unperformed_sender(cmd, params):
            return {
                "status": "ok",
                "result": {
                    "performed": False,
                    "resolution_errors": ["Modifier section not found on basemesh"]
                }
            }

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_unperformed_sender
        )

        resp = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "performed=False" in resp.error_message
        assert resp.verified is False

    def test_apply_bridge_timeout(self, temp_db):
        """Handle timeout when communicating with bridge."""
        import time
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        def mock_slow_sender(cmd, params):
            time.sleep(0.5)
            return {"status": "ok"}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_slow_sender,
            default_timeout=0.1
        )

        resp = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "timed out" in resp.error_message
        assert resp.verified is False

    def test_apply_incorrect_post_read_values(self, temp_db):
        """Fail verification if post-read value does not match expected proposed value."""
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        # Bridge claimed performed=True, but post read is still 0.20 or wrong!
        post_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state, post_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        def mock_sender(cmd, params):
            return {"status": "ok", "result": {"performed": True}}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        resp = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "Target value mismatch" in resp.error_message
        assert resp.verified is False

    def test_apply_unrelated_feature_changed_post_mutation(self, temp_db):
        """Fail verification if an unrelated feature was modified during mutation."""
        initial_state = make_mock_live_state({
            "nose_width": (0.20, False, None, None),
            "chin_width": (-0.10, False, None, None)
        })
        pre_state = make_mock_live_state({
            "nose_width": (0.20, False, None, None),
            "chin_width": (-0.10, False, None, None)
        })
        # nose_width changed to 0.25 (expected), but chin_width unexpectedly changed to 0.50!
        post_state = make_mock_live_state({
            "nose_width": (0.25, False, None, None),
            "chin_width": (0.50, False, None, None)
        })

        mock_state = SequenceStateService([initial_state, pre_state, post_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        def mock_sender(cmd, params):
            return {"status": "ok", "result": {"performed": True}}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        resp = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "unexpectedly modified" in resp.error_message
        assert resp.verified is False

    def test_apply_replay_protection(self, temp_db):
        """Ensure the same preview_log_id cannot be applied more than once."""
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        post_state = make_mock_live_state({"nose_width": (0.25, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state, post_state])
        refine_service = RefinementService(db=temp_db, state_service=mock_state)

        preview = refine_service.process_dry_run(RefinementRequest(
            text="Make the nose slightly wider.",
            use_live_state=True
        ))

        sender_calls = 0
        def mock_sender(cmd, params):
            nonlocal sender_calls
            sender_calls += 1
            return {"status": "ok", "result": {"performed": True}}

        mutation_svc = BlenderMutationService(
            db=temp_db,
            state_service=mock_state,
            command_sender=mock_sender
        )

        # First apply: succeeds
        resp1 = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))
        assert resp1.status == "APPLIED"
        assert sender_calls == 1

        # Second apply with same preview_id: must be rejected by replay protection
        resp2 = mutation_svc.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview.log_id,
            confirm_apply=True
        ))
        assert resp2.status == "APPLY_FAILED"
        assert "already been claimed or applied" in resp2.error_message
        assert "replay protection" in resp2.error_message
        assert sender_calls == 1  # Sender must NOT be called again


class TestApiApplyIntegration:
    """FastAPI integration tests for the POST /apply route."""

    def test_api_apply_success(self, monkeypatch, tmp_path):
        """End-to-end FastAPI test for preview generation followed by successful apply."""
        test_db = Database(tmp_path / "api_apply_test.db")
        initial_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        pre_state = make_mock_live_state({"nose_width": (0.20, False, None, None)})
        post_state = make_mock_live_state({"nose_width": (0.25, False, None, None)})

        mock_state = SequenceStateService([initial_state, pre_state, post_state])
        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        # Patch application services
        test_mutation = BlenderMutationService(
            db=test_db,
            state_service=mock_state,
            command_sender=mock_sender
        )
        test_refine = RefinementService(db=test_db, state_service=mock_state)

        import backend.main as main_mod
        monkeypatch.setattr(main_mod, "refinement_service", test_refine)
        monkeypatch.setattr(main_mod, "mutation_service", test_mutation)

        client = TestClient(app)

        # 1. Preview via POST /refine
        refine_resp = client.post("/refine", json={
            "text": "Make the nose slightly wider.",
            "use_live_state": True,
            "case_id": "API-CASE-001"
        })
        assert refine_resp.status_code == 200
        preview_data = refine_resp.json()
        assert preview_data["status"] == "PREVIEW_READY"
        preview_id = preview_data["log_id"]

        # 2. Apply via POST /apply
        apply_resp = client.post("/apply", json={
            "preview_log_id": preview_id,
            "case_id": "API-CASE-001",
            "character_name": "Human",
            "confirm_apply": True
        })
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["status"] == "APPLIED"
        assert apply_data["verified"] is True
        assert apply_data["drift_checked"] is True
        assert apply_data["applied_value"] == 0.25
        assert len(bridge_calls) == 1

        # 3. Repeat apply -> must fail replay protection
        repeat_resp = client.post("/apply", json={
            "preview_log_id": preview_id,
            "case_id": "API-CASE-001",
            "character_name": "Human",
            "confirm_apply": True
        })
        assert repeat_resp.status_code == 200
        repeat_data = repeat_resp.json()
        assert repeat_data["status"] == "APPLY_FAILED"
        assert "already been claimed or applied" in repeat_data["error_message"]
        assert len(bridge_calls) == 1

    def test_multi_feature_batch_apply_success(self, temp_db):
        """
        Verify multi-feature batch application:
        - 5 features proposed: nose_width, cheekbone_prominence, chin_width, eye_size, head_width.
        - Generates 7 morph target modifiers sent in ONE single 'set_targets' bridge command.
        - Pre-mutation drift check verifies all 5 targets and all 5 unrelated features.
        - Post-mutation read-back verifies all 5 targets within 0.001 and confirms 5 unrelated features unchanged.
        """
        from backend.parser.ollama_parser import OllamaRefinementParser
        from backend.parser.ollama_client import OllamaClient

        # Mock Ollama returning 5 features
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

        ai_client = OllamaClient(http_sender=mock_ai)
        ai_parser = OllamaRefinementParser(client=ai_client)

        # Baseline:
        # nose_width = 0.20 -> prop: 0.25
        # cheekbone_prominence = (left: 0.15, right: 0.20) -> prop: (left: 0.20, right: 0.25)
        # chin_width = -0.10 -> prop: -0.15
        # eye_size = (left: 0.10, right: 0.10) -> prop: (left: 0.05, right: 0.05)
        # head_width = -0.15 -> prop: -0.20
        #
        # Unrelated features (must stay identical):
        # nose_height (0.05), chin_prominence (0.10), forehead_size (0.00), head_height (0.10), mouth_width (-0.05)
        initial_state = make_mock_live_state()

        post_mutation_state = make_mock_live_state(feature_overrides={
            "nose_width": (0.25, False, None, None),
            "cheekbone_prominence": (0.20, True, 0.20, 0.25),
            "chin_width": (-0.15, False, None, None),
            "eye_size": (0.05, True, 0.05, 0.05),
            "head_width": (-0.20, False, None, None),
        })

        mock_state = SequenceStateService([
            initial_state,       # 1. Preview generation (POST /refine)
            initial_state,       # 2. Pre-mutation drift check (POST /apply)
            post_mutation_state  # 3. Post-mutation read-back verification (POST /apply)
        ])

        bridge_dispatches = []
        def mock_sender(cmd, params):
            bridge_dispatches.append((cmd, params))
            return {
                "status": "ok",
                "result": {"performed": True, "changes": [{"name": "Human", "target": "all"}]}
            }

        refine_srv = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        # Step 1: Generate multi-feature preview
        preview_req = RefinementRequest(
            text="A person with a broad nose, prominent cheekbones, a slightly pointed chin, small eyes, and a narrow face.",
            case_id="BATCH-CASE-001",
            character_name="Human",
            use_live_state=True,
            parser_mode="ai"
        )
        preview_resp = refine_srv.process_dry_run(preview_req)

        assert preview_resp.status == "PREVIEW_READY"
        assert preview_resp.feature_id == "multi_feature"
        assert len(preview_resp.features) == 5
        assert len(preview_resp.proposed_payload.modifiers) == 7
        assert preview_resp.proposed_payload.symmetry is False
        assert preview_resp.proposed_payload.prune is True
        assert preview_resp.proposed_payload.refit is False

        # Step 2: Apply multi-feature batch
        apply_req = RefinementApplyRequest(
            preview_log_id=preview_resp.log_id,
            case_id="BATCH-CASE-001",
            character_name="Human",
            confirm_apply=True
        )
        apply_resp = mutation_srv.apply_refinement(apply_req)

        assert apply_resp.status == "APPLIED"
        assert apply_resp.verified is True
        assert apply_resp.drift_checked is True
        assert apply_resp.feature_id == "multi_feature"
        assert len(apply_resp.features_applied) == 5

        # Verify only ONE bridge dispatch occurred
        assert len(bridge_dispatches) == 1
        cmd, params = bridge_dispatches[0]
        assert cmd == "set_targets"
        assert params["name"] == "Human"
        assert len(params["modifiers"]) == 7
        assert params["symmetry"] is False
        assert params["prune"] is True
        assert params["refit"] is False

        # Verify each feature in features_applied
        applied_dict = {f["feature_id"]: f for f in apply_resp.features_applied}
        assert applied_dict["nose_width"]["applied_value"] == 0.25
        assert applied_dict["cheekbone_prominence"]["applied_left_value"] == 0.20
        assert applied_dict["cheekbone_prominence"]["applied_right_value"] == 0.25
        assert applied_dict["chin_width"]["applied_value"] == -0.15
        assert applied_dict["eye_size"]["applied_left_value"] == 0.05
        assert applied_dict["eye_size"]["applied_right_value"] == 0.05
        assert applied_dict["head_width"]["applied_value"] == -0.20
        assert all(f["verified"] is True for f in apply_resp.features_applied)

    def test_multi_feature_batch_apply_state_drift_abortion(self, temp_db):
        """
        Verify state drift abortion on multi-feature batch:
        If any feature in the batch has drifted before application, the apply is aborted
        and NO mutation command is sent to Blender.
        """
        from backend.parser.ollama_parser import OllamaRefinementParser
        from backend.parser.ollama_client import OllamaClient

        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "head_width", "direction": "decrease", "magnitude": "slight"}
                        ]
                    })
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai)
        ai_parser = OllamaRefinementParser(client=ai_client)

        initial_state = make_mock_live_state()

        # State drifted on head_width between preview and apply: -0.15 -> -0.40
        drifted_state = make_mock_live_state(feature_overrides={
            "head_width": (-0.40, False, None, None)
        })

        mock_state = SequenceStateService([
            initial_state,  # Preview
            drifted_state   # Pre-mutation check -> drift detected!
        ])

        bridge_dispatches = []
        def mock_sender(cmd, params):
            bridge_dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        preview_resp = refine_srv.process_dry_run(RefinementRequest(
            text="Wider nose and narrower head.",
            case_id="DRIFT-CASE-001",
            use_live_state=True,
            parser_mode="ai"
        ))
        assert preview_resp.status == "PREVIEW_READY"

        apply_resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview_resp.log_id,
            case_id="DRIFT-CASE-001",
            character_name="Human",
            confirm_apply=True
        ))

        assert apply_resp.status == "APPLY_FAILED"
        assert apply_resp.verified is False
        assert "State drift detected" in apply_resp.error_message
        assert "head width" in apply_resp.error_message.lower()
        # Ensure zero mutation commands were sent
        assert len(bridge_dispatches) == 0

    def test_multi_feature_batch_apply_read_back_mismatch_failure(self, temp_db):
        """
        Verify post-mutation read-back failure:
        If one target in the batch fails to reach its expected value, apply reports failure.
        """
        from backend.parser.ollama_parser import OllamaRefinementParser
        from backend.parser.ollama_client import OllamaClient

        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "chin_width", "direction": "decrease", "magnitude": "slight"}
                        ]
                    })
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai)
        ai_parser = OllamaRefinementParser(client=ai_client)

        initial_state = make_mock_live_state()

        # In post-mutation, nose_width is 0.25 (correct), but chin_width is -0.11 instead of -0.15!
        mismatched_post = make_mock_live_state(feature_overrides={
            "nose_width": (0.25, False, None, None),
            "chin_width": (-0.11, False, None, None)  # Mismatch! Expected -0.15
        })

        mock_state = SequenceStateService([
            initial_state,   # Preview
            initial_state,   # Pre-mutation check (matches)
            mismatched_post  # Post-mutation read-back (mismatch)
        ])

        bridge_dispatches = []
        def mock_sender(cmd, params):
            bridge_dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        preview_resp = refine_srv.process_dry_run(RefinementRequest(
            text="Wider nose and narrower chin.",
            case_id="VERIF-CASE-001",
            use_live_state=True,
            parser_mode="ai"
        ))
        assert preview_resp.status == "PREVIEW_READY"

        apply_resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview_resp.log_id,
            case_id="VERIF-CASE-001",
            character_name="Human",
            confirm_apply=True
        ))

        assert apply_resp.status == "APPLY_FAILED"
        assert apply_resp.verified is False
        assert "Target value mismatch" in apply_resp.error_message
        assert "chin width" in apply_resp.error_message.lower()

    def test_multi_feature_batch_apply_unrelated_feature_changed_failure(self, temp_db):
        """
        Verify post-mutation read-back failure when an unrelated allowlisted feature changed:
        If 'mouth_width' (not in the batch) was unexpectedly changed, verification fails.
        """
        from backend.parser.ollama_parser import OllamaRefinementParser
        from backend.parser.ollama_client import OllamaClient

        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "chin_width", "direction": "decrease", "magnitude": "slight"}
                        ]
                    })
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai)
        ai_parser = OllamaRefinementParser(client=ai_client)

        initial_state = make_mock_live_state()

        # Both target features applied correctly, but mouth_width unexpectedly drifted from -0.05 to +0.30!
        unrelated_changed_post = make_mock_live_state(feature_overrides={
            "nose_width": (0.25, False, None, None),
            "chin_width": (-0.15, False, None, None),
            "mouth_width": (0.30, False, None, None)  # Unexpected modification!
        })

        mock_state = SequenceStateService([
            initial_state,          # Preview
            initial_state,          # Pre-mutation check (matches)
            unrelated_changed_post  # Post-mutation read-back (unrelated changed)
        ])

        bridge_dispatches = []
        def mock_sender(cmd, params):
            bridge_dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        preview_resp = refine_srv.process_dry_run(RefinementRequest(
            text="Wider nose and narrower chin.",
            case_id="UNREL-CASE-001",
            use_live_state=True,
            parser_mode="ai"
        ))
        assert preview_resp.status == "PREVIEW_READY"

        apply_resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=preview_resp.log_id,
            case_id="UNREL-CASE-001",
            character_name="Human",
            confirm_apply=True
        ))

        assert apply_resp.status == "APPLY_FAILED"
        assert apply_resp.verified is False
        assert "Unrelated feature" in apply_resp.error_message
        assert "mouth width" in apply_resp.error_message.lower()

    def test_apply_new_phase1_single_feature_unsided(self, temp_db):
        """Phase 1: Apply newly allowlisted unsided control (jaw_width)."""
        initial_state = make_mock_live_state()
        post_state = make_mock_live_state(feature_overrides={
            "jaw_width": (0.05, False, None, None)
        })

        mock_state = SequenceStateService([
            initial_state,  # preview read
            initial_state,  # pre-mutation drift check
            post_state      # post-mutation read-back
        ])

        dispatches = []
        def mock_sender(cmd, params):
            dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Make the jaw wider.",
            case_id="JAW-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.feature_id == "jaw_width"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="JAW-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.drift_checked is True
        assert len(dispatches) == 1
        cmd, params = dispatches[0]
        assert cmd == "set_targets"
        assert params["modifiers"] == [{
            "section": "chin",
            "category": "chin-jaw-drop-decr-incr",
            "side": "unsided",
            "value": 0.05
        }]

    def test_apply_new_phase1_single_feature_bilateral(self, temp_db):
        """Phase 1: Apply newly allowlisted bilateral control (ear_protrusion)."""
        initial_state = make_mock_live_state()
        post_state = make_mock_live_state(feature_overrides={
            "ear_protrusion": (0.05, True, 0.05, 0.05)
        })

        mock_state = SequenceStateService([
            initial_state,  # preview read
            initial_state,  # pre-mutation drift check
            post_state      # post-mutation read-back
        ])

        dispatches = []
        def mock_sender(cmd, params):
            dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Make the ears stick out more.",
            case_id="EAR-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.feature_id == "ear_protrusion"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="EAR-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.drift_checked is True
        assert len(dispatches) == 1
        cmd, params = dispatches[0]
        assert cmd == "set_targets"
        assert len(params["modifiers"]) == 2
        assert params["modifiers"][0] == {
            "section": "ears",
            "category": "ear-wing-decr-incr",
            "side": "left",
            "value": 0.05
        }
        assert params["modifiers"][1] == {
            "section": "ears",
            "category": "ear-wing-decr-incr",
            "side": "right",
            "value": 0.05
        }

    def test_apply_new_phase1_multi_feature_batch(self, temp_db):
        """Phase 1: Apply composite batch of newly allowlisted features (jaw, hump, upper lip, ears)."""
        def mock_ai(method, url, payload):
            return {
                "message": {
                    "content": json.dumps({
                        "features": [
                            {"feature_id": "jaw_width", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "nasal_bridge_hump", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "mouth_upperlip_volume", "direction": "increase", "magnitude": "slight"},
                            {"feature_id": "ear_protrusion", "direction": "increase", "magnitude": "slight"}
                        ]
                    })
                }
            }

        ai_client = OllamaClient(http_sender=mock_ai)
        ai_parser = OllamaRefinementParser(client=ai_client)

        initial_state = make_mock_live_state()
        post_state = make_mock_live_state(feature_overrides={
            "jaw_width": (0.05, False, None, None),
            "nasal_bridge_hump": (0.05, False, None, None),
            "mouth_upperlip_volume": (0.05, False, None, None),
            "ear_protrusion": (0.05, True, 0.05, 0.05)
        })

        mock_state = SequenceStateService([
            initial_state,  # preview read
            initial_state,  # pre-mutation drift check
            post_state      # post-mutation read-back
        ])

        dispatches = []
        def mock_sender(cmd, params):
            dispatches.append((cmd, params))
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, ai_parser=ai_parser, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="A person with a wide jaw, a dorsal hump on the nose, fuller upper lip, and protruding ears.",
            case_id="COMP-001",
            use_live_state=True,
            parser_mode="ai"
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.feature_id == "multi_feature"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="COMP-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.drift_checked is True
        assert resp.modifiers_applied is not None
        assert len(resp.modifiers_applied) == 5  # 3 unsided + 2 bilateral sides
        assert len(dispatches) == 1
        cmd, params = dispatches[0]
        assert cmd == "set_targets"
        assert len(params["modifiers"]) == 5


class TestAssetMutationSafetyAndExecution:
    """Integration tests for Phase 2 hairstyle and eyebrow mutations via BlenderMutationService."""

    def test_apply_hair_swap(self, temp_db):
        """Verify successful hairstyle swap: remove old hair, add new hair, and post-read verification."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        post_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.bob01",
                object_type="Hair",
                asset_source="bob01/bob01.mhclo",
                asset_id="bob01"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {
                    "status": "ok",
                    "result": {
                        "added": True,
                        "asset_object_name": "Human.bob01",
                        "object_type": params["object_type"],
                        "asset_source": params["fragment"]
                    }
                }
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Change hairstyle to a bob cut.",
            case_id="HAIR-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.asset_adjustments is not None
        assert len(prev.asset_adjustments) == 1
        assert prev.asset_adjustments[0].proposed_asset_id == "bob01"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="HAIR-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.drift_checked is True
        assert resp.assets_applied is not None
        assert len(resp.assets_applied) == 1
        assert resp.assets_applied[0]["asset_id"] == "bob01"
        assert resp.assets_applied[0]["applied_asset_name"] == "Human.bob01"

        # Verify bridge calls: remove old hair, add new hair
        assert len(bridge_calls) == 2
        assert bridge_calls[0][0] == "remove_asset"
        assert bridge_calls[0][1]["name"] == "Human.short01"
        assert bridge_calls[1][0] == "add_asset"
        assert bridge_calls[1][1]["fragment"] == "bob01/bob01.mhclo"

    def test_apply_bald_removal(self, temp_db):
        """Verify bald request only calls remove_asset and verifies equipped_hair is None."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        post_state = make_mock_live_state(
            equipped_hair=None,
            custom_assets=True
        )
        mock_state = SequenceStateService([initial_state, initial_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Make the suspect bald.",
            case_id="BALD-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.asset_adjustments[0].action == "remove"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="BALD-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert len(bridge_calls) == 1
        assert bridge_calls[0][0] == "remove_asset"
        assert bridge_calls[0][1]["name"] == "Human.short01"

    def test_apply_eyebrow_swap(self, temp_db):
        """Verify eyebrow swap: removes old eyebrow and adds new eyebrow."""
        initial_state = make_mock_live_state(
            equipped_eyebrows=EquippedAssetInfo(
                name="Human.eyebrow003",
                object_type="Eyebrows",
                asset_source="eyebrow003/eyebrow003.mhclo",
                asset_id="eyebrow003"
            )
        )
        post_state = make_mock_live_state(
            equipped_eyebrows=EquippedAssetInfo(
                name="Human.eyebrow009",
                object_type="Eyebrows",
                asset_source="eyebrow009/eyebrow009.mhclo",
                asset_id="eyebrow009"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {
                    "status": "ok",
                    "result": {
                        "added": True,
                        "asset_object_name": "Human.eyebrow009",
                        "object_type": params["object_type"],
                        "asset_source": params["fragment"]
                    }
                }
            return {"status": "ok", "result": {"performed": True}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Curved eyebrows.",
            case_id="BROW-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.asset_adjustments[0].proposed_asset_id == "eyebrow009"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="BROW-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert len(bridge_calls) == 2
        assert bridge_calls[0][0] == "remove_asset"
        assert bridge_calls[0][1]["name"] == "Human.eyebrow003"
        assert bridge_calls[1][0] == "add_asset"
        assert bridge_calls[1][1]["fragment"] == "eyebrow009/eyebrow009.mhclo"

    def test_apply_simultaneous_assets_and_geometry(self, temp_db):
        """Verify applying both assets and geometry in a single transaction."""
        initial_state = make_mock_live_state(
            feature_overrides={"jaw_width": (0.0, False, None, None)},
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        post_state = make_mock_live_state(
            feature_overrides={"jaw_width": (0.05, False, None, None)},
            equipped_hair=EquippedAssetInfo(
                name="Human.afro01",
                object_type="Hair",
                asset_source="afro01/afro01.mhclo",
                asset_id="afro01"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {
                    "status": "ok",
                    "result": {
                        "added": True,
                        "asset_object_name": "Human.afro01",
                        "object_type": params["object_type"],
                        "asset_source": params["fragment"]
                    }
                }
            elif cmd == "set_targets":
                return {"status": "ok", "result": {"performed": True}}
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="A suspect with an afro and a wide jaw.",
            case_id="COMB-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.features is not None and len(prev.features) == 1
        assert prev.asset_adjustments is not None and len(prev.asset_adjustments) == 1

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="COMB-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.modifiers_applied is not None
        assert resp.assets_applied is not None
        # Verify 3 commands executed in order: remove hair, add afro, set_targets
        cmds = [call[0] for call in bridge_calls]
        assert cmds == ["remove_asset", "add_asset", "set_targets"]

    def test_apply_asset_drift_detection(self, temp_db):
        """Verify apply is rejected when hairstyle in Blender drifts prior to mutation."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        # Pre-live state shows hair drifted to long01
        drifted_pre_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.long01",
                object_type="Hair",
                asset_source="long01/long01.mhclo",
                asset_id="long01"
            )
        )
        mock_state = SequenceStateService([initial_state, drifted_pre_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Change hairstyle to a bob cut.",
            case_id="DRIFT-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="DRIFT-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert resp.drift_checked is True
        assert "State drift detected for hairstyle" in resp.message
        assert len(bridge_calls) == 0  # No mutation commands dispatched

    def test_apply_hair_when_no_eyebrows_equipped(self, temp_db):
        """Verify hairstyle can be applied when character in Blender has no eyebrows (no false drift)."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            ),
            equipped_eyebrows=None,
            custom_assets=True
        )
        pre_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            ),
            equipped_eyebrows=None,
            custom_assets=True
        )
        post_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.long01",
                object_type="Hair",
                asset_source="long01/long01.mhclo",
                asset_id="long01"
            ),
            equipped_eyebrows=None,
            custom_assets=True
        )
        mock_state = SequenceStateService([initial_state, pre_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {"status": "ok", "result": {"added": True, "asset_object_name": f"Human.{params['fragment'].split('/')[0]}"}}
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Change the hairstyle to long hair.",
            case_id="NO-EB-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.asset_adjustments is not None
        assert prev.asset_adjustments[0].proposed_asset_id == "long01"

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="NO-EB-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        assert resp.error_message is None
        assert "State drift detected" not in (resp.message or "")
        cmds = [call[0] for call in bridge_calls]
        assert cmds == ["remove_asset", "add_asset"]

    def test_apply_eyebrows_when_no_eyebrows_previously_equipped(self, temp_db):
        """Verify eyebrows can be added when character in Blender previously had none."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            ),
            equipped_eyebrows=None,
            custom_assets=True
        )
        pre_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            ),
            equipped_eyebrows=None,
            custom_assets=True
        )
        post_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            ),
            equipped_eyebrows=EquippedAssetInfo(
                name="Human.eyebrow006",
                object_type="Eyebrows",
                asset_source="eyebrow006/eyebrow006.mhclo",
                asset_id="eyebrow006"
            ),
            custom_assets=True
        )
        mock_state = SequenceStateService([initial_state, pre_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "add_asset":
                return {"status": "ok", "result": {"added": True, "asset_object_name": f"Human.{params['fragment'].split('/')[0]}"}}
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Thin curved eyebrows.",
            case_id="ADD-EB-001",
            use_live_state=True
        ))
        assert prev.status == "PREVIEW_READY"
        assert prev.asset_adjustments is not None
        assert prev.asset_adjustments[0].action == "add"
        assert prev.asset_adjustments[0].current_asset_id is None

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="ADD-EB-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLIED"
        assert resp.verified is True
        # remove_asset was not called because there were no eyebrows to remove
        cmds = [call[0] for call in bridge_calls]
        assert cmds == ["add_asset"]

    def test_apply_asset_rollback_on_add_failure(self, temp_db):
        """Verify rollback restores old hair if add_asset fails."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                # Fails during add
                return {"status": "error", "message": "Failed to load mhclo asset"}
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Change hairstyle to a bob cut.",
            case_id="ROLL-001",
            use_live_state=True
        ))

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="ROLL-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "Bridge failed to add hairstyle" in resp.message
        # Rollback check:
        # 1. remove_asset(Human.short01)
        # 2. add_asset(bob01) -> fails
        # 3. rollback: add_asset(short01)
        cmds = [call[0] for call in bridge_calls]
        assert cmds == ["remove_asset", "add_asset", "add_asset"]
        assert bridge_calls[2][1]["fragment"] == "short01/short01.mhclo"

    def test_apply_asset_rollback_on_geometry_failure(self, temp_db):
        """Verify rollback restores original asset if geometry set_targets fails."""
        initial_state = make_mock_live_state(
            feature_overrides={"jaw_width": (0.0, False, None, None)},
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {
                    "status": "ok",
                    "result": {
                        "added": True,
                        "asset_object_name": "Human.afro01",
                        "object_type": params["object_type"],
                        "asset_source": params["fragment"]
                    }
                }
            elif cmd == "set_targets":
                return {"status": "error", "message": "Morph target computation failed"}
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="A suspect with an afro and a wide jaw.",
            case_id="ROLL-002",
            use_live_state=True
        ))

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="ROLL-002",
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert "Bridge returned error status during 'set_targets'" in resp.message
        # Rollback check:
        # 1. remove_asset(Human.short01)
        # 2. add_asset(afro01)
        # 3. set_targets -> fails
        # 4. rollback remove_asset(Human.afro01)
        # 5. rollback add_asset(short01)
        cmds = [call[0] for call in bridge_calls]
        assert cmds == ["remove_asset", "add_asset", "set_targets", "remove_asset", "add_asset"]
        assert bridge_calls[3][1]["name"] == "Human.afro01"
        assert bridge_calls[4][1]["fragment"] == "short01/short01.mhclo"

    def test_apply_asset_readback_verification_failure(self, temp_db):
        """Verify rollback occurs when post-mutation read-back does not observe expected asset."""
        initial_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        # Post state incorrectly still has short01 instead of bob01
        post_state = make_mock_live_state(
            equipped_hair=EquippedAssetInfo(
                name="Human.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01"
            )
        )
        mock_state = SequenceStateService([initial_state, initial_state, post_state])

        bridge_calls = []
        def mock_sender(cmd, params):
            bridge_calls.append((cmd, params))
            if cmd == "remove_asset":
                return {"status": "ok", "result": {"removed": True, "object_name": params["name"]}}
            elif cmd == "add_asset":
                return {
                    "status": "ok",
                    "result": {
                        "added": True,
                        "asset_object_name": "Human.bob01",
                        "object_type": params["object_type"],
                        "asset_source": params["fragment"]
                    }
                }
            return {"status": "ok", "result": {}}

        refine_srv = RefinementService(db=temp_db, state_service=mock_state)
        mutation_srv = BlenderMutationService(db=temp_db, state_service=mock_state, command_sender=mock_sender)

        prev = refine_srv.process_dry_run(RefinementRequest(
            text="Change hairstyle to a bob cut.",
            case_id="VERIF-001",
            use_live_state=True
        ))

        resp = mutation_srv.apply_refinement(RefinementApplyRequest(
            preview_log_id=prev.log_id,
            case_id="VERIF-001",
            confirm_apply=True
        ))

        assert resp.status == "APPLY_FAILED"
        assert resp.verified is False
        assert "Post-mutation read-back verification failed" in resp.message
        # Verify rollback executed
        cmds = [call[0] for call in bridge_calls]
        assert "remove_asset" in cmds and "add_asset" in cmds

