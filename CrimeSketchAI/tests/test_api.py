"""
Integration tests for CrimeSketchAI FastAPI endpoints with State Hardening.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.storage.database import Database

@pytest.fixture
def client(tmp_path):
    test_db = Database(tmp_path / "api_test.db")
    from backend.main import service
    service.db = test_db
    return TestClient(app)

class TestApiEndpoints:
    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "dry_run"
        assert data["state_model"] == "offline_cached_reference"
        assert "CrimeSketchAI" in data["app"]

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["allowlist_count"] == 38
        assert "nose_width" in data["allowlist_features"]
        assert "mouth_upperlip_volume" in data["allowlist_features"]
        assert "jaw_width" in data["allowlist_features"]
        assert "ear_size" in data["allowlist_features"]
        assert data["mode"] == "dry_run"
        assert data["data_source_mode"] == "offline_cached_reference"
        assert data["database_connected"] is True

    def test_features_endpoint(self, client):
        resp = client.get("/features")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 38
        
        nose = next(f for f in data if f["feature_id"] == "nose_width")
        assert nose["reference_value"] == 0.20
        assert nose["value_source"] == "cached_reference"
        assert nose["is_sided"] is False
        assert nose["sides"] == ["unsided"]
        assert nose["target_identifiers"] == ["nose:nose-scale-horiz-decr-incr:unsided"]

        eyes = next(f for f in data if f["feature_id"] == "eye_size")
        assert eyes["reference_value"] == 0.10
        assert eyes["is_sided"] is True
        assert eyes["sides"] == ["left", "right"]
        assert eyes["target_identifiers"] == [
            "eyes:eye-scale-decr-incr:left",
            "eyes:eye-scale-decr-incr:right"
        ]

        upperlip = next(f for f in data if f["feature_id"] == "mouth_upperlip_volume")
        assert upperlip["reference_value"] == 0.00
        assert upperlip["is_sided"] is False
        assert upperlip["target_identifiers"] == ["mouth:mouth-upperlip-volume-decr-incr:unsided"]

        ears = next(f for f in data if f["feature_id"] == "ear_size")
        assert ears["reference_value"] == 0.00
        assert ears["is_sided"] is True
        assert ears["target_identifiers"] == [
            "ears:ear-scale-decr-incr:left",
            "ears:ear-scale-decr-incr:right"
        ]

    def test_refine_endpoint_success(self, client):
        payload = {
            "text": "Make the nose slightly wider.",
            "case_id": "CASE-API-101",
            "character_name": "Human"
        }
        resp = client.post("/refine", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PREVIEW_READY"
        assert data["mode"] == "dry_run"
        assert data["feature_id"] == "nose_width"
        
        # State audit verification
        assert data["reference_value"] == 0.20
        assert data["current_value"] == 0.20
        assert data["value_source"] == "cached_reference"
        assert data["is_live_blender_value"] is False
        assert data["proposed_delta"] == 0.05
        assert data["proposed_value"] == 0.25
        assert data["target_identifier"] == "nose:nose-scale-horiz-decr-incr:unsided"
        assert data["target_identifiers"] == ["nose:nose-scale-horiz-decr-incr:unsided"]
        assert data["target_shapekeys"] == ["nose-scale-horiz-incr"]
        assert data["proposed_payload"]["modifiers"][0]["category"] == "nose-scale-horiz-decr-incr"

    def test_refine_endpoint_rejects_client_current_value(self, client):
        """A client must not be able to claim or override Blender model state."""
        payload = {
            "text": "Make the nose slightly wider.",
            "case_id": "CASE-INJECT-VAL",
            "current_value": 0.95
        }
        resp = client.post("/refine", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert "Caller-supplied 'current_value' is rejected" in data["error_message"]
        assert data["proposed_payload"] is None

        # Verify rejection is logged
        log_resp = client.get("/logs?case_id=CASE-INJECT-VAL")
        assert log_resp.status_code == 200
        logs = log_resp.json()
        assert len(logs) == 1
        assert logs[0]["status"] == "REJECTED"
        assert "Caller-supplied 'current_value' is rejected" in logs[0]["error_message"]

    def test_refine_endpoint_bilateral_preview(self, client):
        payload = {
            "text": "Make the cheekbones more prominent.",
            "case_id": "CASE-API-CHEEK"
        }
        resp = client.post("/refine", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PREVIEW_READY"
        assert data["feature_id"] == "cheekbone_prominence"
        assert data["reference_value"] == 0.15
        assert data["proposed_value"] == 0.20
        assert len(data["proposed_payload"]["modifiers"]) == 2
        sides = {m["side"] for m in data["proposed_payload"]["modifiers"]}
        assert sides == {"left", "right"}
        assert data["target_identifiers"] == [
            "cheek:cheek-bones-decr-incr:left",
            "cheek:cheek-bones-decr-incr:right"
        ]
        assert data["target_shapekeys"] == ["l-cheek-bones-incr", "r-cheek-bones-incr"]

    def test_refine_endpoint_rejected_out_of_scope(self, client):
        payload = {
            "text": "Make the suspect look happier.",
            "case_id": "CASE-API-REJECT"
        }
        resp = client.post("/refine", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert "expression" in data["error_message"].lower()

    def test_logs_endpoint(self, client):
        client.post("/refine", json={"text": "Make the eyes slightly larger.", "case_id": "CASE-AUDIT-1"})
        resp = client.get("/logs?case_id=CASE-AUDIT-1")
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["case_id"] == "CASE-AUDIT-1"
        assert logs[0]["parsed_feature"] == "eye size"
