"""
Unit tests for CrimeSketchAI RefinementService, State Hardening, and Boundary Handling.
"""

import pytest
from pathlib import Path
from backend.storage.database import Database
from backend.service.refinement_service import RefinementService
from backend.models.schemas import RefinementRequest
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST, FeatureDefinition

@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_refinements.db"
    return Database(db_file)

@pytest.fixture
def service(temp_db):
    return RefinementService(db=temp_db)

class TestServiceDryRunStateHardening:
    def test_dry_run_nose_width_uses_cached_reference(self, service, temp_db):
        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-9001",
            character_name="Human"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.mode == "dry_run"
        assert res.feature_id == "nose_width"
        
        # State verification: strictly cached reference, not live Blender read
        assert res.reference_value == 0.20
        assert res.current_value == 0.20
        assert res.value_source == "cached_reference"
        assert res.is_live_blender_value is False
        assert "NOT a live Blender socket read" in res.reference_note

        # Adjustment verification
        assert res.proposed_delta == 0.05
        assert res.proposed_value == 0.25
        assert res.is_boundary_clamped is False
        assert res.boundary_warning is None

        # Targets verification
        assert res.target_identifier == "nose:nose-scale-horiz-decr-incr:unsided"
        assert res.target_identifiers == ["nose:nose-scale-horiz-decr-incr:unsided"]
        assert res.target_shapekeys == ["nose-scale-horiz-incr"]

        # Payload verification
        assert res.proposed_payload is not None
        assert res.proposed_payload.name == "Human"
        assert len(res.proposed_payload.modifiers) == 1
        assert res.proposed_payload.modifiers[0].section == "nose"
        assert res.proposed_payload.modifiers[0].category == "nose-scale-horiz-decr-incr"
        assert res.proposed_payload.modifiers[0].side == "unsided"
        assert res.proposed_payload.modifiers[0].value == 0.25
        assert res.proposed_payload.prune is True
        assert res.proposed_payload.refit is False

        # SQLite audit log verification
        logs = temp_db.get_logs(case_id="CASE-9001")
        assert len(logs) == 1
        assert logs[0]["status"] == "PREVIEW_READY"
        assert logs[0]["parsed_feature"] == "nose width"
        assert logs[0]["current_value"] == 0.20
        assert logs[0]["proposed_delta"] == 0.05
        assert logs[0]["proposed_value"] == 0.25

    def test_caller_supplied_current_value_is_strictly_rejected(self, service, temp_db):
        """Verify that a client cannot assert or override Blender model state."""
        req = RefinementRequest(
            text="Make the nose slightly wider.",
            case_id="CASE-ATTEMPT-OVERRIDE",
            current_value=0.85  # Forbidden attempt to claim current value is 0.85
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "Caller-supplied 'current_value' is rejected" in res.error_message
        assert res.proposed_payload is None

        # Verify rejection is permanently audited in SQLite
        logs = temp_db.get_logs(case_id="CASE-ATTEMPT-OVERRIDE")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        assert "Caller-supplied 'current_value' is rejected" in logs[0]["error_message"]

        # Verify catalog reference value is completely unaffected
        assert VERIFIED_ALLOWLIST["nose_width"].reference_value == 0.20

    def test_bilateral_feature_representation_cheekbones(self, service):
        """Bilateral features must represent both left and right targets explicitly."""
        req = RefinementRequest(
            text="Make the cheekbones more prominent.",
            case_id="CASE-BILATERAL-CHEEK"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.feature_id == "cheekbone_prominence"
        assert res.reference_value == 0.15
        assert res.proposed_value == 0.20

        # Must explicitly generate both left and right modifiers
        assert len(res.proposed_payload.modifiers) == 2
        mod_left = next(m for m in res.proposed_payload.modifiers if m.side == "left")
        mod_right = next(m for m in res.proposed_payload.modifiers if m.side == "right")
        assert mod_left.value == 0.20
        assert mod_right.value == 0.20
        assert mod_left.category == "cheek-bones-decr-incr"
        assert mod_right.category == "cheek-bones-decr-incr"

        # Check target identifiers and shape keys
        assert res.target_identifiers == [
            "cheek:cheek-bones-decr-incr:left",
            "cheek:cheek-bones-decr-incr:right"
        ]
        assert res.target_shapekeys == ["l-cheek-bones-incr", "r-cheek-bones-incr"]

    def test_bilateral_feature_decrease_eyes(self, service):
        """Test bilateral decrease produces correct negative shape keys on both sides."""
        req = RefinementRequest(
            text="Make the eyes smaller.",
            case_id="CASE-BILATERAL-EYES"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.feature_id == "eye_size"
        assert res.reference_value == 0.10
        assert res.proposed_value == 0.05
        assert len(res.proposed_payload.modifiers) == 2
        assert res.target_identifiers == [
            "eyes:eye-scale-decr-incr:left",
            "eyes:eye-scale-decr-incr:right"
        ]
        assert res.target_shapekeys == ["l-eye-scale-decr", "r-eye-scale-decr"]

    def test_unsupported_request_logged(self, service, temp_db):
        req = RefinementRequest(
            text="Change the skin tone to tan.",
            case_id="CASE-UNSUPPORTED"
        )
        res = service.process_dry_run(req)

        assert res.status == "REJECTED"
        assert "Skin material/tone modifications are handled via skin tools" in res.error_message

        logs = temp_db.get_logs(case_id="CASE-UNSUPPORTED")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"


class TestSliderBoundaryHandling:
    def test_upper_boundary_clamping_with_mock_feature(self, service, monkeypatch):
        """Verify upper clamping when reference value + delta exceeds +1.0."""
        # Temporarily mock forehead_size reference value to 0.98
        mock_forehead = FeatureDefinition(
            feature_id="forehead_size",
            display_name="forehead size",
            section="forehead",
            category="forehead-scale-vert-decr-incr",
            is_sided=False,
            sides=("unsided",),
            min_value=-1.0,
            max_value=1.0,
            reference_value=0.98,
            adjustment_step=0.05,
            positive_targets=("forehead-scale-vert-incr",),
            negative_targets=("forehead-scale-vert-decr",),
            increase_keywords=("larger", "taller", "higher", "bigger", "increase size", "increase height", "make taller"),
            decrease_keywords=("smaller", "shorter", "lower", "decrease size", "decrease height", "make shorter"),
            description="Forehead vertical height."
        )
        monkeypatch.setitem(VERIFIED_ALLOWLIST, "forehead_size", mock_forehead)

        req = RefinementRequest(text="Make the forehead taller.")
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.is_boundary_clamped is True
        assert res.proposed_value == 1.0
        assert "reaches the maximum slider limit" in res.boundary_warning

    def test_lower_boundary_clamping_with_mock_feature(self, service, monkeypatch):
        """Verify lower clamping when reference value - delta drops below -1.0."""
        mock_chin = FeatureDefinition(
            feature_id="chin_width",
            display_name="chin width",
            section="chin",
            category="chin-width-decr-incr",
            is_sided=False,
            sides=("unsided",),
            min_value=-1.0,
            max_value=1.0,
            reference_value=-0.98,
            adjustment_step=0.05,
            positive_targets=("chin-width-incr",),
            negative_targets=("chin-width-decr",),
            increase_keywords=("wider", "broad", "broader", "widen"),
            decrease_keywords=("narrower", "narrow", "pointier", "pointed", "slimmer", "slim"),
            description="Chin horizontal width."
        )
        monkeypatch.setitem(VERIFIED_ALLOWLIST, "chin_width", mock_chin)

        req = RefinementRequest(text="Make the chin narrower.")
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.is_boundary_clamped is True
        assert res.proposed_value == -1.0
        assert "reaches the minimum slider limit" in res.boundary_warning

    def test_character_name_whitespace_trimmed_and_fallback(self, service):
        req = RefinementRequest(
            text="Make the nose slightly wider.",
            character_name="   "
        )
        res = service.process_dry_run(req)
        assert res.status == "PREVIEW_READY"
        assert res.proposed_payload.name == "Human"

    def test_rejection_logs_include_value_source(self, service, temp_db):
        req = RefinementRequest(
            text="Make his hair purple.",
            case_id="CASE-REJECT-VAL-SOURCE",
            use_live_state=False
        )
        res = service.process_dry_run(req)
        assert res.status == "REJECTED"

        logs = temp_db.get_logs(case_id="CASE-REJECT-VAL-SOURCE")
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        import json
        details = json.loads(logs[0]["details_json"])
        assert details["value_source"] == "cached_reference"

    def test_dry_run_hairstyle_preview(self, service, temp_db):
        """Verify hairstyle preview generation in offline cached reference mode."""
        req = RefinementRequest(
            text="Change the hairstyle to a bob cut.",
            case_id="CASE-HAIR-BOB",
            character_name="Human"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.mode == "dry_run"
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_type == "hair"
        assert adj.current_asset_id == "short01"
        assert adj.proposed_asset_id == "bob01"
        assert adj.action == "swap"
        assert res.proposed_payload.modifiers == []

        logs = temp_db.get_logs(case_id="CASE-HAIR-BOB")
        assert len(logs) == 1
        assert logs[0]["status"] == "PREVIEW_READY"

    def test_dry_run_bald_preview(self, service):
        """Verify bald preview sets action to remove."""
        req = RefinementRequest(
            text="Make the suspect bald with thick eyebrows.",
            case_id="CASE-BALD-EYEBROWS"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].proposed_asset_id == "bald"
        assert types["hair"].action == "remove"
        assert types["eyebrows"].proposed_asset_id == "eyebrow010"
        assert types["eyebrows"].action == "swap"

    def test_dry_run_combined_assets_and_geometry(self, service):
        """Verify simultaneous geometry adjustments and hairstyle swaps in a single preview."""
        req = RefinementRequest(
            text="A suspect with an afro and a wide jaw.",
            case_id="CASE-AFRO-JAW"
        )
        res = service.process_dry_run(req)

        assert res.status == "PREVIEW_READY"
        assert res.feature_id == "jaw_width"
        assert len(res.features) == 1
        assert res.features[0].feature_id == "jaw_width"
        assert res.features[0].adjustment_delta == 0.05
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        assert res.asset_adjustments[0].proposed_asset_id == "afro01"
        assert len(res.proposed_payload.modifiers) == 1

