"""
Unit and Integration Tests for Forensic Sketch Rendering Service & Endpoint.
"""

from pathlib import Path
import os
import subprocess
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app, sketch_service
from backend.models.schemas import SketchRenderRequest, SketchRenderResponse
from backend.service.sketch_render_service import SketchRenderService, apply_pencil_sketch_filter


@pytest.fixture
def tmp_dirs(tmp_path):
    output_dir = tmp_path / "sketches"
    export_dir = tmp_path / "exports"
    output_dir.mkdir()
    export_dir.mkdir()
    fake_blender = tmp_path / "blender.exe"
    fake_blender.write_text("fake binary")
    return {
        "output_dir": output_dir,
        "export_dir": export_dir,
        "blender_exe": fake_blender,
        "root": tmp_path
    }


def create_dummy_raw_image(filepath: Path, width=1024, height=1024):
    """Creates a dummy grayscale raw render image."""
    img = Image.new("L", (width, height), color=200)
    # Put a dark rectangle in the middle
    for x in range(300, 700):
        for y in range(300, 700):
            img.putpixel((x, y), 50)
    img.save(filepath, format="PNG")


def test_reject_non_human_character(tmp_dirs):
    service = SketchRenderService(
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"]
    )
    req = SketchRenderRequest(character_name="Alien", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert resp.character_name == "Alien"
    assert "not supported" in resp.message
    assert "Hard object locking" in resp.error_message


def test_reject_blender_exe_not_found(tmp_dirs):
    non_existent = tmp_dirs["root"] / "no_blender.exe"
    service = SketchRenderService(
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=non_existent
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "Blender executable not found" in resp.message


def test_bridge_communication_exception(tmp_dirs):
    def failing_sender(cmd, args):
        raise ConnectionRefusedError("MPFB Bridge socket unreachable at 127.0.0.1:9877")

    service = SketchRenderService(
        command_sender=failing_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"]
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "Failed to communicate with Blender MPFB Bridge" in resp.message
    assert "unreachable" in resp.error_message


def test_bridge_export_command_error(tmp_dirs):
    def error_sender(cmd, args):
        return {
            "status": "error",
            "protocol_version": 2,
            "error": "object_not_found",
            "message": "Object 'Human' not found in current scene."
        }

    service = SketchRenderService(
        command_sender=error_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"]
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "Blender MPFB Bridge export command failed" in resp.message
    assert "Object 'Human' not found" in resp.message


def test_bridge_export_not_exported_flag(tmp_dirs):
    def not_exported_sender(cmd, args):
        return {
            "status": "ok",
            "protocol_version": 2,
            "result": {
                "exported": False,
                "message": "Export was aborted due to empty mesh."
            }
        }

    service = SketchRenderService(
        command_sender=not_exported_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"]
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "Blender character was not exported successfully" in resp.message


def test_headless_subprocess_timeout(tmp_dirs):
    fake_glb = tmp_dirs["export_dir"] / "test.glb"
    fake_glb.write_text("fake glb")

    def mock_sender(cmd, args):
        return {
            "status": "ok",
            "protocol_version": 2,
            "result": {
                "exported": True,
                "path": str(fake_glb)
            }
        }

    def timing_out_runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10.0)

    service = SketchRenderService(
        command_sender=mock_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"],
        runner=timing_out_runner,
        timeout=10.0
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "timed out after 10.0 seconds" in resp.message


def test_headless_subprocess_nonzero_exit(tmp_dirs):
    fake_glb = tmp_dirs["export_dir"] / "test.glb"
    fake_glb.write_text("fake glb")

    def mock_sender(cmd, args):
        return {
            "status": "ok",
            "protocol_version": 2,
            "result": {
                "exported": True,
                "path": str(fake_glb)
            }
        }

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "CUDA out of memory"
    mock_proc.stdout = ""

    def failing_runner(cmd, **kwargs):
        return mock_proc

    service = SketchRenderService(
        command_sender=mock_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"],
        runner=failing_runner
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-01")
    resp = service.render_sketch(req)

    assert resp.status == "FAILED"
    assert "failed with return code 1" in resp.message
    assert "CUDA out of memory" in resp.error_message


def test_successful_render_pipeline(tmp_dirs):
    fake_glb = tmp_dirs["export_dir"] / "test.glb"
    fake_glb.write_text("fake glb content")

    def mock_sender(cmd, args):
        return {
            "status": "ok",
            "protocol_version": 2,
            "result": {
                "exported": True,
                "path": str(fake_glb)
            }
        }

    # Runner that creates the expected raw render image
    def successful_runner(cmd, **kwargs):
        # Find raw render path from the python script or kwargs
        # In our service, the raw image is in tmp_dirs["output_dir"] with prefix "raw_"
        raw_files = list(tmp_dirs["output_dir"].glob("raw_*.png"))
        # If not created yet, look for the python script and extract filepath
        script_files = list(tmp_dirs["output_dir"].glob("render_script_*.py"))
        assert len(script_files) == 1
        script_text = script_files[0].read_text()
        assert "ForensicCamera" in script_text
        assert "BLENDER_WORKBENCH" in script_text

        # Create dummy raw 1024x1024 image matching what Blender Workbench outputs
        for line in script_text.splitlines():
            if "filepath =" in line:
                target_raw = line.split('"')[1]
                create_dummy_raw_image(Path(target_raw))

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""
        mock_proc.stdout = "Render completed"
        return mock_proc

    service = SketchRenderService(
        command_sender=mock_sender,
        output_dir=tmp_dirs["output_dir"],
        export_dir=tmp_dirs["export_dir"],
        blender_exe=tmp_dirs["blender_exe"],
        runner=successful_runner
    )
    req = SketchRenderRequest(character_name="Human", case_id="CASE-FORENSIC-001")
    resp = service.render_sketch(req)

    assert resp.status == "SUCCESS"
    assert resp.character_name == "Human"
    assert resp.case_id == "CASE-FORENSIC-001"
    assert resp.image_url.startswith("/sketches/sketch_")
    assert resp.filename.endswith(".png")
    assert resp.dimensions == [1024, 1024]
    assert resp.filesize_bytes > 0
    assert Path(resp.filepath).exists()

    # Verify output image is a valid 1024x1024 PNG
    with Image.open(resp.filepath) as im:
        assert im.format == "PNG"
        assert im.size == (1024, 1024)

    # Verify temporary files were cleaned up
    assert not fake_glb.exists()
    assert len(list(tmp_dirs["output_dir"].glob("raw_*.png"))) == 0
    assert len(list(tmp_dirs["output_dir"].glob("render_script_*.py"))) == 0


def test_apply_pencil_sketch_filter(tmp_path):
    raw_path = tmp_path / "raw.png"
    out_path = tmp_path / "sketch.png"
    create_dummy_raw_image(raw_path, 1024, 1024)

    apply_pencil_sketch_filter(raw_path, out_path)

    assert out_path.exists()
    with Image.open(out_path) as im:
        assert im.format == "PNG"
        assert im.size == (1024, 1024)


def test_api_render_sketch_endpoint():
    client = TestClient(app)

    # Mock the sketch_service.render_sketch method
    mock_resp = SketchRenderResponse(
        status="SUCCESS",
        character_name="Human",
        case_id="API-TEST-99",
        image_url="/sketches/sketch_20261029_test.png",
        filename="sketch_20261029_test.png",
        filepath="C:/Dept/CrimeSketchAI/sketches/sketch_20261029_test.png",
        filesize_bytes=123456,
        dimensions=[1024, 1024],
        timestamp_utc="2026-10-29T00:00:00Z",
        message="Forensic pencil sketch successfully generated for 'Human'."
    )

    with patch.object(sketch_service, "render_sketch", return_value=mock_resp) as mock_render:
        payload = {
            "character_name": "Human",
            "case_id": "API-TEST-99"
        }
        res = client.post("/render-sketch", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["character_name"] == "Human"
        assert data["case_id"] == "API-TEST-99"
        assert data["image_url"] == "/sketches/sketch_20261029_test.png"
        assert data["dimensions"] == [1024, 1024]
        assert data["filesize_bytes"] == 123456
        mock_render.assert_called_once()


def test_api_render_sketch_rejected_character():
    client = TestClient(app)
    payload = {
        "character_name": "Alien",
        "case_id": "API-TEST-REJECT"
    }
    res = client.post("/render-sketch", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "FAILED"
    assert "not supported" in data["message"]

