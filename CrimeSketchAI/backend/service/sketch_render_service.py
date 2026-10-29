"""
Forensic Sketch Render Service for CrimeSketchAI.

Renders a clean, monochrome forensic pencil-sketch-style portrait from the actual,
currently applied Blender character 'Human' (including facial geometry, hair, and eyebrows).

SAFETY CONSTRAINTS:
1. Strict character locking: Operates exclusively on character name 'Human'.
2. Non-destructive: Does NOT alter or save over the active .blend file.
3. Isolated execution: Runs Blender headless with --factory-startup to prevent port/state collisions.
4. Clean cleanup: Removes temporary export (.glb), script, and intermediate render files.
5. Deterministic local pipeline: 100% offline, no cloud or paid services.
"""

from datetime import datetime, timezone
from pathlib import Path
import os
import re
import subprocess
import uuid
from typing import Optional, Dict, Any, Callable, List

from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np

from backend.config import settings
from backend.models.schemas import SketchRenderRequest, SketchRenderResponse

try:
    from mpfbmcp import bridge_connection
except ImportError:
    bridge_connection = None


def apply_pencil_sketch_filter(raw_image_path: Path, output_image_path: Path) -> None:
    """
    Transforms a raw 3D Workbench clay/cavity render into a clean, monochrome
    forensic pencil-sketch portrait with crisp graphite contour lines and tonal shading.
    """
    img = Image.open(raw_image_path).convert("L")
    raw_np = np.array(img, dtype=np.float32)

    # Detect white/near-white background from raw render
    bg_mask = raw_np > 248.0

    # Invert and apply Gaussian blur to produce dodge shadow mask
    img_inv = ImageOps.invert(img)
    img_blur = img_inv.filter(ImageFilter.GaussianBlur(radius=5))
    blur_np = np.array(img_blur, dtype=np.float32)

    # Color dodge calculates crisp pencil contour lines: base * 255 / (255 - blur)
    dodge_np = np.clip((raw_np * 255.0) / (255.0 - blur_np + 1e-5), 0, 255)

    # Blend line art (65%) with soft graphite tonal shading (35%) to maintain 3D facial depth
    sketch_np = 0.65 * dodge_np + 0.35 * raw_np

    # Enforce pure white background (#FFFFFF) for forensic sketch report presentation
    sketch_np[bg_mask] = 255.0

    sketch_img = Image.fromarray(np.clip(sketch_np, 0, 255).astype(np.uint8))

    # Enhance contrast slightly to simulate authentic 2B/4B forensic graphite strokes
    enhancer = ImageEnhance.Contrast(sketch_img)
    final_sketch = enhancer.enhance(1.15)

    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    final_sketch.save(output_image_path, format="PNG")


class SketchRenderService:
    def __init__(
        self,
        command_sender: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        blender_exe: Optional[Path | str] = None,
        output_dir: Optional[Path] = None,
        export_dir: Optional[Path] = None,
        timeout: Optional[float] = None,
        runner: Optional[Callable[..., Any]] = None
    ):
        self._command_sender = command_sender
        self.blender_exe = Path(blender_exe or settings.BLENDER_EXECUTABLE)
        self.output_dir = Path(output_dir or settings.SKETCH_OUTPUT_DIR)
        self.export_dir = Path(export_dir or settings.MPFB_EXPORT_DIR)
        self.timeout = timeout or settings.SKETCH_RENDER_TIMEOUT_SECONDS
        self._runner = runner or subprocess.run

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_sender(self) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
        if self._command_sender is not None:
            return self._command_sender
        if bridge_connection is not None:
            return bridge_connection.send_command
        raise RuntimeError(
            "The 'mpfbmcp' package is not installed or importable. "
            "Ensure the virtual environment is properly activated."
        )

    def _generate_render_script(self, glb_path: Path, raw_render_path: Path) -> str:
        """Generates the python script for headless Blender execution."""
        glb_str = glb_path.resolve().as_posix()
        raw_str = raw_render_path.resolve().as_posix()

        return f"""import bpy
import bmesh
import math
import sys

# 1. Start with clean empty scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import exported GLTF character
bpy.ops.import_scene.gltf(filepath="{glb_str}")

# 3. Strip MakeHuman helper geometry (verts >= 13380 on basemesh)
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH' and len(obj.data.vertices) >= 13380:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        helpers = [v for v in bm.verts if v.index >= 13380]
        bmesh.ops.delete(bm, geom=helpers, context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

# 4. Configure front-facing portrait camera
# Standard 85mm portrait lens, framed directly at face (head center ~ 1.51m)
cam_data = bpy.data.cameras.new("ForensicCamera")
cam_data.lens = 85.0
cam_data.sensor_width = 36.0
cam_obj = bpy.data.objects.new("ForensicCamera", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# Camera located at X=0, Y=-0.92, Z=1.51 looking directly along +Y
cam_obj.location = (0.0, -0.92, 1.51)
cam_obj.rotation_euler = (math.radians(90), 0.0, 0.0)

# 5. Scene & Workbench render settings
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = "{raw_str}"

# Shading: cavity ridges & valleys + crisp object outline for forensic sketch lines
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'SINGLE'
shading.single_color = (0.85, 0.85, 0.85)
shading.show_cavity = True
shading.cavity_type = 'BOTH'
shading.cavity_ridge_factor = 1.6
shading.cavity_valley_factor = 1.6
shading.show_object_outline = True
shading.object_outline_color = (0.05, 0.05, 0.05)

# World background: pure white
world = bpy.data.worlds.new("SketchWorld")
world.color = (1.0, 1.0, 1.0)
scene.world = world

# 6. Render still
bpy.ops.render.render(write_still=True)
"""

    def render_sketch(self, request: SketchRenderRequest) -> SketchRenderResponse:
        now_utc = datetime.now(timezone.utc)
        timestamp_iso = now_utc.isoformat()
        timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")

        char_name = (request.character_name or settings.DEFAULT_CHARACTER_NAME).strip()

        # Hard object locking safety check
        if char_name != settings.DEFAULT_CHARACTER_NAME:
            return SketchRenderResponse(
                status="FAILED",
                character_name=char_name,
                case_id=request.case_id,
                timestamp_utc=timestamp_iso,
                message=f"Character '{char_name}' is not supported. Only '{settings.DEFAULT_CHARACTER_NAME}' is permitted.",
                error_message="Hard object locking prohibits rendering characters other than 'Human'."
            )

        # Sanitize case identifier for safe filesystem usage
        safe_case = "unassigned"
        if request.case_id and request.case_id.strip():
            safe_case = re.sub(r"[^a-zA-Z0-9_\-]", "_", request.case_id.strip())[:32]

        unique_id = uuid.uuid4().hex[:6]
        output_filename = f"sketch_{timestamp_str}_{safe_case}_{unique_id}.png"
        output_filepath = self.output_dir / output_filename

        raw_filename = f"raw_{timestamp_str}_{unique_id}.png"
        raw_filepath = self.output_dir / raw_filename

        script_filename = f"render_script_{timestamp_str}_{unique_id}.py"
        script_filepath = self.output_dir / script_filename

        export_name = f"sketch_export_{timestamp_str}_{unique_id}"
        expected_glb_path = self.export_dir / f"{export_name}.glb"

        resolved_glb_path: Optional[Path] = None

        try:
            # 1. Verify Blender executable exists before attempting export
            if not self.blender_exe.is_file():
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message=f"Blender executable not found at '{self.blender_exe}'.",
                    error_message=f"Path '{self.blender_exe}' does not exist or is not a file."
                )

            # 2. Export character from live Blender session via MPFB Bridge
            try:
                sender = self._get_sender()
                export_resp = sender("export_character", {
                    "name": char_name,
                    "export_name": export_name,
                    "format": "gltf",
                    "overwrite": True
                })
            except Exception as e:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Failed to communicate with Blender MPFB Bridge during character export.",
                    error_message=str(e)
                )

            if export_resp.get("status") != "ok":
                err = export_resp.get("message") or export_resp.get("error") or "Unknown bridge export error"
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message=f"Blender MPFB Bridge export command failed: {err}",
                    error_message=str(export_resp)
                )

            result_data = export_resp.get("result", {})
            if not result_data.get("exported", False):
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Blender character was not exported successfully.",
                    error_message=result_data.get("message", "Character not exported.")
                )

            # Resolve actual exported file path
            reported_path_str = result_data.get("path")
            if reported_path_str and Path(reported_path_str).exists():
                resolved_glb_path = Path(reported_path_str)
            elif expected_glb_path.exists():
                resolved_glb_path = expected_glb_path
            else:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Exported character GLTF file was not found on disk.",
                    error_message=f"Expected GLB at '{expected_glb_path}'."
                )

            # 3. Write headless Blender render script
            script_content = self._generate_render_script(resolved_glb_path, raw_filepath)
            script_filepath.write_text(script_content, encoding="utf-8")

            # 4. Execute headless Blender render in an isolated process
            cmd = [
                str(self.blender_exe),
                "--background",
                "--factory-startup",
                "--python",
                str(script_filepath)
            ]

            try:
                proc = self._runner(cmd, capture_output=True, text=True, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message=f"Blender render process timed out after {self.timeout} seconds.",
                    error_message="Subprocess timed out during headless rendering."
                )
            except Exception as e:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Failed to spawn Blender headless render subprocess.",
                    error_message=str(e)
                )

            if proc.returncode != 0:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message=f"Blender headless render failed with return code {proc.returncode}.",
                    error_message=proc.stderr or proc.stdout or "Non-zero exit code."
                )

            if not raw_filepath.is_file() or raw_filepath.stat().st_size == 0:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Blender render completed but raw image was not produced or is empty.",
                    error_message=f"Expected raw render file at '{raw_filepath}'."
                )

            # 5. Apply pencil sketch filter post-processing
            try:
                apply_pencil_sketch_filter(raw_filepath, output_filepath)
            except Exception as e:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Pencil sketch post-processing filter failed.",
                    error_message=str(e)
                )

            # 6. Verify final sketch output file exists, is readable, and meets dimensions
            if not output_filepath.is_file() or output_filepath.stat().st_size == 0:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Final sketch image was not generated or is empty.",
                    error_message=f"Expected sketch file at '{output_filepath}'."
                )

            try:
                with Image.open(output_filepath) as img_verify:
                    width, height = img_verify.size
                    dimensions = [width, height]
            except Exception as e:
                return SketchRenderResponse(
                    status="FAILED",
                    character_name=char_name,
                    case_id=request.case_id,
                    timestamp_utc=timestamp_iso,
                    message="Generated sketch image could not be verified by image parser.",
                    error_message=str(e)
                )

            filesize = output_filepath.stat().st_size

            return SketchRenderResponse(
                status="SUCCESS",
                character_name=char_name,
                case_id=request.case_id,
                image_url=f"/sketches/{output_filename}",
                filename=output_filename,
                filepath=str(output_filepath.resolve()),
                filesize_bytes=filesize,
                dimensions=dimensions,
                timestamp_utc=timestamp_iso,
                message=f"Forensic pencil sketch successfully generated for '{char_name}'.",
                error_message=None
            )

        finally:
            # Clean up intermediate temporary files
            for temp_path in [raw_filepath, script_filepath, resolved_glb_path]:
                if temp_path is not None:
                    try:
                        if Path(temp_path).exists():
                            Path(temp_path).unlink()
                    except Exception:
                        pass

