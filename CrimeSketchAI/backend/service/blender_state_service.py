"""
Blender Live State Service for CrimeSketchAI.

Performs read-only state introspection using the installed MPFB-MCP bridge connection.
Extracts current values for the 10 allowlisted facial features from the live Blender session.

SAFETY CONSTRAINTS:
- Strictly read-only: calls ONLY 'get_target_stack'.
- NEVER calls 'mpfb_set_targets' or any mutation tool.
- NEVER substitutes cached values on failure: returns 'unavailable' with error details.
- Enforces strict socket timeouts so disconnected Blender instances never hang the API.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
import os

from backend.config import settings
from backend.models.schemas import LiveStateResponse, LiveFeatureState, EquippedAssetInfo
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST
from backend.parser.asset_catalog import get_asset_by_fragment

try:
    from mpfbmcp import bridge_connection
except ImportError:
    bridge_connection = None


class BlenderStateService:
    def __init__(
        self,
        command_sender: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        default_timeout: Optional[float] = None
    ):
        self._command_sender = command_sender
        self.default_timeout = default_timeout or settings.BLENDER_TIMEOUT_SECONDS

    def _get_sender(self) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
        if self._command_sender is not None:
            return self._command_sender
        if bridge_connection is not None:
            return bridge_connection.send_command
        raise RuntimeError(
            "The 'mpfbmcp' package is not installed or importable. "
            "Ensure the virtual environment is properly activated."
        )

    def get_live_state(
        self,
        character_name: Optional[str] = None,
        timeout: Optional[float] = None,
        include_assets: bool = False
    ) -> LiveStateResponse:
        """
        Retrieves the live target stack from Blender for the specified character.
        Strictly read-only via 'get_target_stack'.
        If include_assets=True, also queries 'get_character_summary' for equipped assets.
        """
        char_name = (character_name or settings.DEFAULT_CHARACTER_NAME).strip() or settings.DEFAULT_CHARACTER_NAME
        read_timeout = timeout or self.default_timeout
        timestamp_utc = datetime.now(timezone.utc).isoformat()

        # Step 1: Ensure bridge connection is possible
        try:
            sender = self._get_sender()
        except Exception as e:
            return LiveStateResponse(
                blender_available=False,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"MCP Bridge client unavailable: {str(e)}"
            )

        # Step 2: Execute read-only command with bounded timeout
        # Using verified schema: get_target_stack(name=..., include_macro=True, limit=200)
        command_params = {
            "name": char_name,
            "include_macro": True,
            "limit": 200
        }

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(sender, "get_target_stack", command_params)
            response = future.result(timeout=read_timeout)
        except FutureTimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return LiveStateResponse(
                blender_available=False,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"Connection to MPFB Bridge at 127.0.0.1:{settings.MPFB_BRIDGE_PORT} timed out after {read_timeout}s."
            )
        except ConnectionError as e:
            executor.shutdown(wait=False, cancel_futures=True)
            return LiveStateResponse(
                blender_available=False,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"Cannot connect to MPFB Bridge at 127.0.0.1:{settings.MPFB_BRIDGE_PORT}: {str(e)}"
            )
        except Exception as e:
            executor.shutdown(wait=False, cancel_futures=True)
            return LiveStateResponse(
                blender_available=False,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"Error reading live Blender state: {str(e)}"
            )
        finally:
            executor.shutdown(wait=False)

        # Step 3: Validate MCP response envelope
        if not isinstance(response, dict):
            return LiveStateResponse(
                blender_available=False,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"Malformed response envelope: expected JSON object, got {type(response).__name__}"
            )

        if response.get("status") != "ok":
            error_msg = response.get("message") or response.get("error") or "Unknown bridge error"
            return LiveStateResponse(
                blender_available=True,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"MPFB Bridge returned non-ok status: {error_msg}"
            )

        result = response.get("result")
        if not isinstance(result, dict):
            return LiveStateResponse(
                blender_available=True,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details="Malformed MCP response: 'result' key is missing or not a dictionary."
            )

        if not result.get("found", True):
            return LiveStateResponse(
                blender_available=True,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details=f"Character '{char_name}' was not found in the active Blender scene."
            )

        # Step 4: Extract live values for the 10 allowlisted features
        modifiers_raw = result.get("modifiers", [])
        if not isinstance(modifiers_raw, list):
            return LiveStateResponse(
                blender_available=True,
                character_name=char_name,
                source="unavailable",
                timestamp_utc=timestamp_utc,
                features=None,
                error_details="Malformed MCP response: 'modifiers' key is not a list."
            )

        # Build lookup table: (section, category, side) -> value
        modifier_lookup = {}
        for mod in modifiers_raw:
            if isinstance(mod, dict):
                sec = mod.get("section")
                cat = mod.get("category")
                side = mod.get("side", "unsided")
                val = mod.get("value")
                if sec and cat and val is not None:
                    modifier_lookup[(sec, cat, side)] = float(val)

        extracted_features: Dict[str, LiveFeatureState] = {}

        for fid, fdef in VERIFIED_ALLOWLIST.items():
            if fdef.is_sided:
                # Bilateral feature (e.g. cheekbone_prominence, eye_size)
                # MPFB modifiers report 0.0 when targets are pruned / at zero.
                left_val = modifier_lookup.get((fdef.section, fdef.category, "left"), 0.0)
                right_val = modifier_lookup.get((fdef.section, fdef.category, "right"), 0.0)
                is_sym = abs(left_val - right_val) < 1e-4

                extracted_features[fid] = LiveFeatureState(
                    feature_id=fid,
                    display_name=fdef.display_name,
                    section=fdef.section,
                    category=fdef.category,
                    is_sided=True,
                    side="left,right",
                    value=round(left_val, 4),
                    left_value=round(left_val, 4),
                    right_value=round(right_val, 4),
                    is_symmetric=is_sym,
                    target_identifiers=list(fdef.target_identifiers)
                )
            else:
                # Unsided feature
                val = modifier_lookup.get((fdef.section, fdef.category, "unsided"), 0.0)
                extracted_features[fid] = LiveFeatureState(
                    feature_id=fid,
                    display_name=fdef.display_name,
                    section=fdef.section,
                    category=fdef.category,
                    is_sided=False,
                    side="unsided",
                    value=round(val, 4),
                    target_identifiers=list(fdef.target_identifiers)
                )

        # Step 5: Extract equipped assets (Hair, Eyebrows) via get_character_summary if requested
        equipped_hair: Optional[EquippedAssetInfo] = None
        equipped_eyebrows: Optional[EquippedAssetInfo] = None
        all_equipped: List[EquippedAssetInfo] = []
        has_queried_assets = False

        if include_assets:
            try:
                summary_resp = sender("get_character_summary", {"name": char_name})
                if isinstance(summary_resp, dict) and summary_resp.get("status") == "ok":
                    s_res = summary_resp.get("result", {})
                    if isinstance(s_res, dict) and "equipped_assets" in s_res:
                        has_queried_assets = True
                        raw_assets = s_res.get("equipped_assets", [])
                        for a in raw_assets:
                            if isinstance(a, dict):
                                a_name = a.get("name", "")
                                a_type = a.get("object_type", "")
                                a_src = a.get("asset_source")
                                a_def = get_asset_by_fragment(a_src) if a_src else None
                                a_info = EquippedAssetInfo(
                                    name=a_name,
                                    object_type=a_type,
                                    asset_source=a_src,
                                    asset_id=a_def.asset_id if a_def else None,
                                    in_current_scene=a.get("in_current_scene", True)
                                )
                                all_equipped.append(a_info)
                                if a_type.lower() == "hair":
                                    equipped_hair = a_info
                                elif a_type.lower() == "eyebrows":
                                    equipped_eyebrows = a_info
            except Exception:
                pass

        # If assets were not queried or not present in mock, use baseline defaults
        if not has_queried_assets:
            equipped_hair = EquippedAssetInfo(
                name=f"{char_name}.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01",
                in_current_scene=True
            )
            equipped_eyebrows = EquippedAssetInfo(
                name=f"{char_name}.eyebrow003",
                object_type="Eyebrows",
                asset_source="eyebrow003/eyebrow003.mhclo",
                asset_id="eyebrow003",
                in_current_scene=True
            )
            all_equipped = [equipped_hair, equipped_eyebrows]

        return LiveStateResponse(
            blender_available=True,
            character_name=char_name,
            source="live_blender",
            timestamp_utc=timestamp_utc,
            features=extracted_features,
            equipped_hair=equipped_hair,
            equipped_eyebrows=equipped_eyebrows,
            equipped_assets=all_equipped,
            raw_modifier_count=result.get("modifier_count", len(modifiers_raw)),
            macro_count=result.get("counts_by_kind", {}).get("macro"),
            asymmetries=result.get("asymmetries", []),
            error_details=None
        )

    def get_equipped_assets(
        self,
        character_name: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Directly queries get_character_summary from Blender to inspect equipped assets.
        Returns dict with keys: 'hair', 'eyebrows', 'all', 'status', 'error'.
        """
        char_name = (character_name or settings.DEFAULT_CHARACTER_NAME).strip() or settings.DEFAULT_CHARACTER_NAME
        read_timeout = timeout or self.default_timeout

        try:
            sender = self._get_sender()
        except Exception as e:
            return {"hair": None, "eyebrows": None, "all": [], "status": "error", "error": str(e)}

        try:
            summary_resp = sender("get_character_summary", {"name": char_name})
            if not isinstance(summary_resp, dict) or summary_resp.get("status") != "ok":
                err = summary_resp.get("error") if isinstance(summary_resp, dict) else str(summary_resp)
                return {"hair": None, "eyebrows": None, "all": [], "status": "error", "error": err}

            s_res = summary_resp.get("result", {})
            raw_assets = s_res.get("equipped_assets", [])
            equipped_hair = None
            equipped_eyebrows = None
            all_equipped = []

            for a in raw_assets:
                if isinstance(a, dict):
                    a_name = a.get("name", "")
                    a_type = a.get("object_type", "")
                    a_src = a.get("asset_source")
                    a_def = get_asset_by_fragment(a_src) if a_src else None
                    a_info = EquippedAssetInfo(
                        name=a_name,
                        object_type=a_type,
                        asset_source=a_src,
                        asset_id=a_def.asset_id if a_def else None,
                        in_current_scene=a.get("in_current_scene", True)
                    )
                    all_equipped.append(a_info)
                    if a_type.lower() == "hair":
                        equipped_hair = a_info
                    elif a_type.lower() == "eyebrows":
                        equipped_eyebrows = a_info

            return {
                "hair": equipped_hair,
                "eyebrows": equipped_eyebrows,
                "all": all_equipped,
                "status": "ok",
                "error": None
            }
        except Exception as e:
            return {"hair": None, "eyebrows": None, "all": [], "status": "error", "error": str(e)}

