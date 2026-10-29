"""
Blender Mutation Service for CrimeSketchAI.

Applies approved refinement changes to the Blender "Human" model via the
verified MPFB MCP 'set_targets' bridge command.

CRITICAL SAFETY ARCHITECTURE:
1. Two-phase commit: Only previously recorded 'PREVIEW_READY' previews can be applied.
2. Server-side modifier retrieval: Modifiers are strictly read from the SQLite audit record,
   NEVER from caller request payload.
3. Allowlist revalidation: Every modifier is re-validated against VERIFIED_ALLOWLIST.
4. Hard object locking: Operates strictly on character name "Human".
5. Atomic replay protection: Uses SQLite PRIMARY KEY constraint to ensure no preview
   can ever be applied more than once, including under concurrent requests.
6. Pre-mutation state drift check: Reads live Blender state immediately before dispatch,
   verifying that neither the target feature nor other allowlisted features have drifted.
7. Verification read-back: Reads live Blender state immediately after mutation,
   verifying target matches expected values (<0.001) and unrelated features did not change.
8. Comprehensive audit logging: Every attempt (success, drift rejection, validation rejection,
   bridge failure, read-back failure) is recorded in SQLite.
"""

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable

from backend.config import settings
from backend.models.schemas import (
    RefinementApplyRequest,
    RefinementApplyResponse,
    LiveStateResponse,
    EquippedAssetInfo
)
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST, FeatureDefinition
from backend.parser.asset_catalog import (
    HAIRSTYLE_CATALOG,
    EYEBROW_CATALOG,
    VERIFIED_ASSET_ALLOWLIST,
    get_asset_by_fragment
)
from backend.service.blender_state_service import BlenderStateService
from backend.storage.database import Database

try:
    from mpfbmcp import bridge_connection
except ImportError:
    bridge_connection = None


class BlenderMutationService:
    def __init__(
        self,
        db: Optional[Database] = None,
        state_service: Optional[BlenderStateService] = None,
        command_sender: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        default_timeout: Optional[float] = None
    ):
        self.db = db or Database()
        self.state_service = state_service or BlenderStateService()
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

    def _execute_rollback(
        self,
        rollback_stack: List[Dict[str, Any]],
        sender: Callable[[str, Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        Rolls back applied asset changes in reverse order if any subsequent operation fails.
        """
        for action_item in reversed(rollback_stack):
            try:
                if action_item["action"] == "remove":
                    sender("remove_asset", {"name": action_item["name"]})
                elif action_item["action"] == "add":
                    sender("add_asset", {
                        "name": "Human",
                        "object_type": action_item["object_type"],
                        "fragment": action_item["fragment"]
                    })
            except Exception:
                pass

    def _failed_apply(
        self,
        request: RefinementApplyRequest,
        feature_id: Optional[str],
        display_name: Optional[str],
        error_msg: str,
        drift_checked: bool = True
    ) -> RefinementApplyResponse:
        log_id = self.db.log_request(
            request_text=f"Apply preview #{request.preview_log_id} to character Human",
            mode="live_apply",
            status="APPLY_FAILED",
            case_id=request.case_id,
            parsed_feature=display_name,
            error_message=error_msg
        )
        return RefinementApplyResponse(
            status="APPLY_FAILED",
            apply_log_id=log_id,
            preview_log_id=request.preview_log_id,
            case_id=request.case_id,
            character_name="Human",
            feature_id=feature_id,
            display_name=display_name,
            verified=False,
            drift_checked=drift_checked,
            message=f"Refinement application rejected: {error_msg}",
            error_message=error_msg
        )

    def apply_refinement(self, request: RefinementApplyRequest) -> RefinementApplyResponse:
        """
        Executes an explicitly approved refinement on the live Blender Human model.
        Strictly applies the exact modifiers previously validated in a PREVIEW_READY preview.
        """
        char_name = (request.character_name or "Human").strip()

        # Step 1: Safety verification - Character name strictly "Human"
        if char_name != "Human":
            error_msg = (
                f"Application rejected: Character name must be exactly 'Human', got '{char_name}'. "
                "Arbitrary scene objects cannot be modified."
            )
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character '{char_name}'",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "character_name": char_name,
                    "confirm_apply": request.confirm_apply
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name=char_name,
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Step 2: Safety verification - Explicit user confirmation
        if not request.confirm_apply:
            error_msg = "Application rejected: Explicit confirmation ('confirm_apply: true') is required to modify Blender."
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "character_name": "Human",
                    "confirm_apply": False
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Step 3: Retrieve preview audit record from SQLite
        preview_record = self.db.get_log_by_id(request.preview_log_id)
        if not preview_record:
            error_msg = f"Application rejected: Preview log ID #{request.preview_log_id} not found."
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "reason": "preview_not_found"
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        if preview_record.get("status") != "PREVIEW_READY":
            status_val = preview_record.get("status")
            error_msg = (
                f"Application rejected: Log ID #{request.preview_log_id} has status '{status_val}'. "
                "Only 'PREVIEW_READY' previews can be applied to Blender."
            )
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "preview_status": status_val
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Step 4: Atomic replay protection claim
        claimed = self.db.claim_preview_for_apply(
            preview_log_id=request.preview_log_id,
            case_id=request.case_id or preview_record.get("case_id"),
            character_name="Human"
        )
        if not claimed:
            applied_info = self.db.get_applied_record(request.preview_log_id)
            prev_status = applied_info.get("status") if applied_info else "ALREADY_CLAIMED"
            prev_time = applied_info.get("applied_at_utc") if applied_info else "earlier"
            error_msg = (
                f"Application rejected: Preview #{request.preview_log_id} has already been claimed or applied "
                f"(status: {prev_status} at {prev_time}). Previews cannot be applied more than once (replay protection)."
            )
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "reason": "replay_protection_triggered",
                    "previous_status": prev_status
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Parse preview details
        details: Dict[str, Any] = {}
        if preview_record.get("details_json"):
            try:
                details = json.loads(preview_record["details_json"])
            except Exception:
                details = {}

        # Step 5: Baseline Sufficiency Verification
        # Previews generated in offline cached reference mode cannot be safely applied
        use_live_state = details.get("use_live_state") is True
        is_live_blender_val = details.get("is_live_blender_value") is True
        if not use_live_state or not is_live_blender_val:
            error_msg = (
                f"Application rejected: Preview #{request.preview_log_id} was generated in offline cached-reference mode "
                "(use_live_state=False). Live Blender baseline data was not captured at preview time. "
                "Previews must be generated with use_live_state=True against the active Blender model to be safely applied."
            )
            self.db.complete_preview_apply(
                preview_log_id=request.preview_log_id,
                status="FAILED",
                error_message=error_msg
            )
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "use_live_state": details.get("use_live_state"),
                    "reason": "missing_live_baseline"
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Step 6: Server-side Modifier Retrieval & Allowlist Revalidation
        proposed_payload = details.get("proposed_payload")
        if not proposed_payload or not isinstance(proposed_payload, dict):
            error_msg = "Application rejected: Preview record is missing a valid 'proposed_payload'."
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        raw_modifiers = proposed_payload.get("modifiers") or []
        if not isinstance(raw_modifiers, list):
            raw_modifiers = []

        raw_asset_adjs = details.get("asset_adjustments") or []
        if not isinstance(raw_asset_adjs, list):
            raw_asset_adjs = []

        if not raw_modifiers and not raw_asset_adjs:
            error_msg = "Application rejected: No modifiers or asset adjustments found in proposed payload."
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                error_message=error_msg
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Validate asset adjustments against catalog
        validated_assets: List[Dict[str, Any]] = []
        for a_idx, a_mod in enumerate(raw_asset_adjs):
            if not isinstance(a_mod, dict):
                error_msg = f"Application rejected: Asset adjustment #{a_idx} is not a valid dictionary."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                log_id = self.db.log_request(
                    request_text=f"Apply preview #{request.preview_log_id} to character Human",
                    mode="live_apply",
                    status="APPLY_FAILED",
                    case_id=request.case_id,
                    error_message=error_msg
                )
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    apply_log_id=log_id,
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    verified=False,
                    drift_checked=False,
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )

            a_type = str(a_mod.get("asset_type", "")).strip().lower()
            prop_id = str(a_mod.get("proposed_asset_id", "")).strip().lower()
            if a_type == "hair":
                if prop_id not in HAIRSTYLE_CATALOG:
                    error_msg = f"Application rejected: Proposed hairstyle '{prop_id}' is not in verified catalog."
                    self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                    return RefinementApplyResponse(
                        status="APPLY_FAILED",
                        preview_log_id=request.preview_log_id,
                        case_id=request.case_id,
                        character_name="Human",
                        message=f"Refinement application rejected: {error_msg}",
                        error_message=error_msg
                    )
            elif a_type == "eyebrows":
                if prop_id not in EYEBROW_CATALOG:
                    error_msg = f"Application rejected: Proposed eyebrow style '{prop_id}' is not in verified catalog."
                    self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                    return RefinementApplyResponse(
                        status="APPLY_FAILED",
                        preview_log_id=request.preview_log_id,
                        case_id=request.case_id,
                        character_name="Human",
                        message=f"Refinement application rejected: {error_msg}",
                        error_message=error_msg
                    )
            else:
                error_msg = f"Application rejected: Unknown asset type '{a_type}'."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )
            validated_assets.append(a_mod)

        # Re-validate every single modifier against VERIFIED_ALLOWLIST
        validated_modifiers: List[Dict[str, Any]] = []
        target_fdefs: Dict[str, FeatureDefinition] = {}

        for idx, mod in enumerate(raw_modifiers):
            if not isinstance(mod, dict):
                error_msg = f"Application rejected: Modifier #{idx} is not a valid dictionary."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                log_id = self.db.log_request(
                    request_text=f"Apply preview #{request.preview_log_id} to character Human",
                    mode="live_apply",
                    status="APPLY_FAILED",
                    case_id=request.case_id,
                    error_message=error_msg
                )
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    apply_log_id=log_id,
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    verified=False,
                    drift_checked=False,
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )

            sec = mod.get("section")
            cat = mod.get("category")
            side = mod.get("side")
            val = mod.get("value")

            # Find matching FeatureDefinition
            matched = [
                f for f in VERIFIED_ALLOWLIST.values()
                if f.section == sec and f.category == cat
            ]
            if not matched:
                error_msg = f"Application rejected: Modifier target '{sec}:{cat}' is not in the verified allowlist."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                log_id = self.db.log_request(
                    request_text=f"Apply preview #{request.preview_log_id} to character Human",
                    mode="live_apply",
                    status="APPLY_FAILED",
                    case_id=request.case_id,
                    error_message=error_msg
                )
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    apply_log_id=log_id,
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    verified=False,
                    drift_checked=False,
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )

            fdef = matched[0]
            target_fdefs[fdef.feature_id] = fdef

            # Validate side
            if fdef.is_sided:
                if side not in ("left", "right"):
                    error_msg = f"Application rejected: Bilateral feature '{fdef.display_name}' requires side 'left' or 'right', got '{side}'."
                    self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                    log_id = self.db.log_request(
                        request_text=f"Apply preview #{request.preview_log_id} to character Human",
                        mode="live_apply",
                        status="APPLY_FAILED",
                        case_id=request.case_id,
                        error_message=error_msg
                    )
                    return RefinementApplyResponse(
                        status="APPLY_FAILED",
                        apply_log_id=log_id,
                        preview_log_id=request.preview_log_id,
                        case_id=request.case_id,
                        character_name="Human",
                        verified=False,
                        drift_checked=False,
                        message=f"Refinement application rejected: {error_msg}",
                        error_message=error_msg
                    )
            else:
                if side != "unsided":
                    error_msg = f"Application rejected: Unsided feature '{fdef.display_name}' requires side 'unsided', got '{side}'."
                    self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                    log_id = self.db.log_request(
                        request_text=f"Apply preview #{request.preview_log_id} to character Human",
                        mode="live_apply",
                        status="APPLY_FAILED",
                        case_id=request.case_id,
                        error_message=error_msg
                    )
                    return RefinementApplyResponse(
                        status="APPLY_FAILED",
                        apply_log_id=log_id,
                        preview_log_id=request.preview_log_id,
                        case_id=request.case_id,
                        character_name="Human",
                        verified=False,
                        drift_checked=False,
                        message=f"Refinement application rejected: {error_msg}",
                        error_message=error_msg
                    )

            # Validate value range
            if not isinstance(val, (int, float)):
                error_msg = f"Application rejected: Modifier value must be numeric, got {type(val).__name__}."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                log_id = self.db.log_request(
                    request_text=f"Apply preview #{request.preview_log_id} to character Human",
                    mode="live_apply",
                    status="APPLY_FAILED",
                    case_id=request.case_id,
                    error_message=error_msg
                )
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    apply_log_id=log_id,
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    verified=False,
                    drift_checked=False,
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )

            val_float = float(val)
            if not (fdef.min_value <= val_float <= fdef.max_value):
                error_msg = (
                    f"Application rejected: Modifier value {val_float} is outside verified bounds "
                    f"[{fdef.min_value}, {fdef.max_value}] for feature '{fdef.display_name}'."
                )
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                log_id = self.db.log_request(
                    request_text=f"Apply preview #{request.preview_log_id} to character Human",
                    mode="live_apply",
                    status="APPLY_FAILED",
                    case_id=request.case_id,
                    error_message=error_msg
                )
                return RefinementApplyResponse(
                    status="APPLY_FAILED",
                    apply_log_id=log_id,
                    preview_log_id=request.preview_log_id,
                    case_id=request.case_id,
                    character_name="Human",
                    verified=False,
                    drift_checked=False,
                    message=f"Refinement application rejected: {error_msg}",
                    error_message=error_msg
                )

            validated_modifiers.append({
                "section": sec,
                "category": cat,
                "side": side,
                "value": round(val_float, 4)
            })

        if target_fdefs:
            batch_features: List[Dict[str, Any]] = details.get("features", [])
            if not batch_features:
                first_fdef = list(target_fdefs.values())[0]
                batch_features = [{
                    "feature_id": first_fdef.feature_id,
                    "display_name": first_fdef.display_name,
                    "is_sided": first_fdef.is_sided,
                    "observed_current_value": details.get("observed_current_value"),
                    "proposed_value": details.get("proposed_value"),
                    "observed_left_value": details.get("observed_left_value"),
                    "observed_right_value": details.get("observed_right_value"),
                    "proposed_left_value": details.get("proposed_left_value"),
                    "proposed_right_value": details.get("proposed_right_value"),
                    "target_identifiers": details.get("target_identifiers", []),
                    "target_shapekeys": details.get("target_shapekeys", [])
                }]
            is_multi = len(batch_features) > 1 or len(target_fdefs) > 1 or len(validated_assets) > 0
            first_fdef = list(target_fdefs.values())[0]
            resp_fid = "multi_feature" if is_multi else first_fdef.feature_id
            resp_display = f"Multi-Feature Batch ({len(batch_features)} features)" if is_multi else first_fdef.display_name
        elif validated_assets:
            batch_features = []
            first_fdef = None
            is_multi = len(validated_assets) > 1
            resp_fid = "asset_customization"
            resp_display = "Hair / Eyebrow Customization"
        else:
            error_msg = "Application rejected: Could not resolve target feature definitions or asset adjustments."
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Step 7: Pre-Mutation Live State Read & State Drift Verification
        try:
            pre_live = self.state_service.get_live_state("Human", include_assets=bool(validated_assets))
        except TypeError:
            pre_live = self.state_service.get_live_state("Human")

        if not pre_live.blender_available or pre_live.source != "live_blender" or (target_fdefs and not pre_live.features):
            error_msg = (
                f"Application rejected: Cannot read live Blender state before mutation: "
                f"{pre_live.error_details or 'MPFB Bridge unavailable'}. Mutation aborted."
            )
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                parsed_feature=resp_display,
                error_message=error_msg,
                details={
                    "preview_log_id": request.preview_log_id,
                    "reason": "pre_read_unavailable",
                    "bridge_error": pre_live.error_details
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                feature_id=resp_fid,
                display_name=resp_display,
                verified=False,
                drift_checked=False,
                message=f"Refinement application rejected: {error_msg}",
                error_message=error_msg
            )

        # Verify state drift across all target features
        drift_detected = False
        drift_msg = ""

        for feat_item in batch_features:
            fid = feat_item.get("feature_id")
            fdef = target_fdefs.get(fid) or VERIFIED_ALLOWLIST.get(fid)
            if not fdef or fid not in pre_live.features:
                drift_detected = True
                drift_msg = f"Target feature '{feat_item.get('display_name', fid)}' missing from live Blender state."
                break

            live_target = pre_live.features[fid]
            if fdef.is_sided:
                exp_left = feat_item.get("observed_left_value")
                exp_right = feat_item.get("observed_right_value")
                if exp_left is None or exp_right is None:
                    drift_detected = True
                    drift_msg = f"Audit record lacks observed bilateral baseline values for '{fdef.display_name}'."
                    break
                elif (abs(live_target.left_value - exp_left) > 0.001 or
                      abs(live_target.right_value - exp_right) > 0.001):
                    drift_detected = True
                    drift_msg = (
                        f"State drift detected for bilateral feature '{fdef.display_name}'. "
                        f"Baseline captured during preview was (left: {exp_left:+.2f}, right: {exp_right:+.2f}), "
                        f"but live Blender model is currently at (left: {live_target.left_value:+.2f}, right: {live_target.right_value:+.2f})."
                    )
                    break
            else:
                exp_val = feat_item.get("observed_current_value")
                if exp_val is None:
                    drift_detected = True
                    drift_msg = f"Audit record lacks observed current value baseline for '{fdef.display_name}'."
                    break
                elif abs(live_target.value - exp_val) > 0.001:
                    drift_detected = True
                    drift_msg = (
                        f"State drift detected for feature '{fdef.display_name}'. "
                        f"Baseline captured during preview was {exp_val:+.2f}, "
                        f"but live Blender model is currently at {live_target.value:+.2f}."
                    )
                    break

        # Also verify live_baseline_snapshot for unrelated features if present
        if not drift_detected and details.get("live_baseline_snapshot"):
            snap = details["live_baseline_snapshot"]
            for other_fid, snap_data in snap.items():
                if other_fid not in target_fdefs and other_fid in pre_live.features:
                    pre_other = pre_live.features[other_fid]
                    if snap_data.get("left_value") is not None:
                        if (abs(pre_other.left_value - snap_data["left_value"]) > 0.001 or
                            abs(pre_other.right_value - snap_data["right_value"]) > 0.001):
                            drift_detected = True
                            drift_msg = (
                                f"State drift detected on unrelated feature '{other_fid}'. "
                                f"Baseline was (left: {snap_data['left_value']:+.2f}, right: {snap_data['right_value']:+.2f}), "
                                f"currently at (left: {pre_other.left_value:+.2f}, right: {pre_other.right_value:+.2f})."
                            )
                            break
                    else:
                        if abs(pre_other.value - snap_data["value"]) > 0.001:
                            drift_detected = True
                            drift_msg = (
                                f"State drift detected on unrelated feature '{other_fid}'. "
                                f"Baseline was {snap_data['value']:+.2f}, currently at {pre_other.value:+.2f}."
                            )
                            break

        # Also verify equipped asset state drift if assets are involved
        if not drift_detected and validated_assets:
            snap_hair = details.get("equipped_hair")
            if snap_hair:
                exp_h = snap_hair.get("asset_source")
                live_h = getattr(pre_live, 'equipped_hair', None)
                live_h_src = live_h.asset_source if live_h else None
                if exp_h != live_h_src:
                    drift_detected = True
                    drift_msg = (
                        f"State drift detected for hairstyle on character 'Human'. "
                        f"Baseline was '{exp_h}', currently '{live_h_src}'."
                    )
            snap_eb = details.get("equipped_eyebrows")
            if snap_eb and not drift_detected:
                exp_eb = snap_eb.get("asset_source")
                live_eb = getattr(pre_live, 'equipped_eyebrows', None)
                live_eb_src = live_eb.asset_source if live_eb else None
                if exp_eb != live_eb_src:
                    drift_detected = True
                    drift_msg = (
                        f"State drift detected for eyebrows on character 'Human'. "
                        f"Baseline was '{exp_eb}', currently '{live_eb_src}'."
                    )

        if drift_detected:
            full_drift_error = f"Application rejected: {drift_msg} Regenerate a fresh preview before applying."
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=full_drift_error)
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                parsed_feature=resp_display,
                error_message=full_drift_error,
                details={
                    "preview_log_id": request.preview_log_id,
                    "reason": "state_drift_detected",
                    "drift_message": drift_msg
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                feature_id=resp_fid,
                display_name=resp_display,
                verified=False,
                drift_checked=True,
                message=f"Refinement application rejected: {full_drift_error}",
                error_message=full_drift_error
            )

        # Baseline values for single feature backward compatibility
        first_live = pre_live.features.get(first_fdef.feature_id) if first_fdef and pre_live.features else None
        prev_val = first_live.value if first_live and not first_fdef.is_sided else None
        prev_left = first_live.left_value if first_live and first_fdef.is_sided else None
        prev_right = first_live.right_value if first_live and first_fdef.is_sided else None

        # Step 8: Send Mutation Commands (Assets and/or 'set_targets') via MPFB Bridge
        try:
            sender = self._get_sender()
        except Exception as e:
            error_msg = f"Application rejected: Bridge client error: {str(e)}"
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            return self._failed_apply(request, resp_fid, resp_display, error_msg, drift_checked=True)

        rollback_stack: List[Dict[str, Any]] = []
        applied_asset_records: List[Dict[str, Any]] = []

        # 8a: Execute Asset Swaps / Removals / Additions
        if validated_assets:
            for asset_item in validated_assets:
                atype = asset_item.get("asset_type")
                action = asset_item.get("action")
                prop_frag = asset_item.get("proposed_fragment")
                prop_id = asset_item.get("proposed_asset_id")
                prop_name = asset_item.get("proposed_display_name")

                if atype == "hair":
                    cur_h = getattr(pre_live, "equipped_hair", None)
                    cur_h_name = cur_h.name if cur_h else asset_item.get("current_asset_name")
                    cur_h_src = cur_h.asset_source if cur_h else asset_item.get("current_fragment")

                    if action == "remove" or prop_id is None or not prop_frag:
                        # Bald request: remove hair if currently equipped
                        if cur_h_name:
                            try:
                                rem_resp = sender("remove_asset", {"name": cur_h_name})
                            except Exception as e:
                                self._execute_rollback(rollback_stack, sender)
                                error_msg = f"Failed to remove hair '{cur_h_name}': {str(e)}"
                                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                                return self._failed_apply(request, resp_fid, resp_display, error_msg)

                            if not isinstance(rem_resp, dict) or rem_resp.get("status") != "ok" or not rem_resp.get("result", {}).get("removed", False):
                                self._execute_rollback(rollback_stack, sender)
                                error_msg = f"Bridge failed to remove hair '{cur_h_name}': {rem_resp}"
                                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                                return self._failed_apply(request, resp_fid, resp_display, error_msg)

                            if cur_h_src:
                                rollback_stack.append({
                                    "action": "add",
                                    "object_type": "Hair",
                                    "fragment": cur_h_src
                                })
                            applied_asset_records.append({
                                "asset_type": "hair",
                                "action": "remove",
                                "removed_asset_name": cur_h_name,
                                "display_name": "Bald",
                                "verified": True
                            })
                        else:
                            applied_asset_records.append({
                                "asset_type": "hair",
                                "action": "remove",
                                "removed_asset_name": None,
                                "display_name": "Bald",
                                "verified": True
                            })
                    else:
                        # Swap or add hair
                        if cur_h_name:
                            try:
                                rem_resp = sender("remove_asset", {"name": cur_h_name})
                            except Exception as e:
                                self._execute_rollback(rollback_stack, sender)
                                error_msg = f"Failed to remove previous hair '{cur_h_name}': {str(e)}"
                                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                                return self._failed_apply(request, resp_fid, resp_display, error_msg)

                            if not isinstance(rem_resp, dict) or rem_resp.get("status") != "ok" or not rem_resp.get("result", {}).get("removed", False):
                                self._execute_rollback(rollback_stack, sender)
                                error_msg = f"Bridge failed to remove previous hair '{cur_h_name}': {rem_resp}"
                                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                                return self._failed_apply(request, resp_fid, resp_display, error_msg)

                            if cur_h_src:
                                rollback_stack.append({
                                    "action": "add",
                                    "object_type": "Hair",
                                    "fragment": cur_h_src
                                })

                        try:
                            add_resp = sender("add_asset", {
                                "name": "Human",
                                "object_type": "Hair",
                                "fragment": prop_frag
                            })
                        except Exception as e:
                            self._execute_rollback(rollback_stack, sender)
                            error_msg = f"Failed to add hairstyle '{prop_frag}': {str(e)}"
                            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                            return self._failed_apply(request, resp_fid, resp_display, error_msg)

                        if not isinstance(add_resp, dict) or add_resp.get("status") != "ok" or not add_resp.get("result", {}).get("added", False):
                            self._execute_rollback(rollback_stack, sender)
                            error_msg = f"Bridge failed to add hairstyle '{prop_frag}': {add_resp}"
                            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                            return self._failed_apply(request, resp_fid, resp_display, error_msg)

                        new_hair_name = add_resp.get("result", {}).get("asset_object_name") or f"Human.{prop_id}"
                        rollback_stack.append({
                            "action": "remove",
                            "name": new_hair_name
                        })
                        applied_asset_records.append({
                            "asset_type": "hair",
                            "action": action,
                            "applied_asset_name": new_hair_name,
                            "asset_id": prop_id,
                            "fragment": prop_frag,
                            "display_name": prop_name,
                            "verified": True
                        })

                elif atype == "eyebrows":
                    cur_eb = getattr(pre_live, "equipped_eyebrows", None)
                    cur_eb_name = cur_eb.name if cur_eb else asset_item.get("current_asset_name")
                    cur_eb_src = cur_eb.asset_source if cur_eb else asset_item.get("current_fragment")

                    if cur_eb_name:
                        try:
                            rem_resp = sender("remove_asset", {"name": cur_eb_name})
                        except Exception as e:
                            self._execute_rollback(rollback_stack, sender)
                            error_msg = f"Failed to remove previous eyebrows '{cur_eb_name}': {str(e)}"
                            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                            return self._failed_apply(request, resp_fid, resp_display, error_msg)

                            if not isinstance(rem_resp, dict) or rem_resp.get("status") != "ok" or not rem_resp.get("result", {}).get("removed", False):
                                self._execute_rollback(rollback_stack, sender)
                                error_msg = f"Bridge failed to remove previous eyebrows '{cur_eb_name}': {rem_resp}"
                                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                                return self._failed_apply(request, resp_fid, resp_display, error_msg)

                        if cur_eb_src:
                            rollback_stack.append({
                                "action": "add",
                                "object_type": "Eyebrows",
                                "fragment": cur_eb_src
                            })

                    try:
                        add_resp = sender("add_asset", {
                            "name": "Human",
                            "object_type": "Eyebrows",
                            "fragment": prop_frag
                        })
                    except Exception as e:
                        self._execute_rollback(rollback_stack, sender)
                        error_msg = f"Failed to add eyebrows '{prop_frag}': {str(e)}"
                        self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                        return self._failed_apply(request, resp_fid, resp_display, error_msg)

                    if not isinstance(add_resp, dict) or add_resp.get("status") != "ok" or not add_resp.get("result", {}).get("added", False):
                        self._execute_rollback(rollback_stack, sender)
                        error_msg = f"Bridge failed to add eyebrows '{prop_frag}': {add_resp}"
                        self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                        return self._failed_apply(request, resp_fid, resp_display, error_msg)

                    new_eb_name = add_resp.get("result", {}).get("asset_object_name") or f"Human.{prop_id}"
                    rollback_stack.append({
                        "action": "remove",
                        "name": new_eb_name
                    })
                    applied_asset_records.append({
                        "asset_type": "eyebrows",
                        "action": action,
                        "applied_asset_name": new_eb_name,
                        "asset_id": prop_id,
                        "fragment": prop_frag,
                        "display_name": prop_name,
                        "verified": True
                    })

        # 8b: Execute Morph Target Modifiers via 'set_targets' (if geometry features present)
        res_obj: Dict[str, Any] = {"performed": True, "changes": []}
        if validated_modifiers:
            params = {
                "name": "Human",
                "modifiers": validated_modifiers,
                "targets": [],
                "symmetry": False,
                "prune": True,
                "refit": False
            }

            executor = ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(sender, "set_targets", params)
                response = future.result(timeout=self.default_timeout)
            except FutureTimeoutError:
                executor.shutdown(wait=False, cancel_futures=True)
                self._execute_rollback(rollback_stack, sender)
                error_msg = f"MPFB Bridge timed out after {self.default_timeout}s during 'set_targets'."
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                return self._failed_apply(request, resp_fid, resp_display, error_msg)
            except Exception as e:
                executor.shutdown(wait=False, cancel_futures=True)
                self._execute_rollback(rollback_stack, sender)
                error_msg = f"Socket error communicating with MPFB Bridge during 'set_targets': {str(e)}"
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                return self._failed_apply(request, resp_fid, resp_display, error_msg)
            finally:
                executor.shutdown(wait=False)

            # Check response envelope
            if not isinstance(response, dict) or response.get("status") != "ok":
                msg = response.get("message") or response.get("error") if isinstance(response, dict) else str(response)
                self._execute_rollback(rollback_stack, sender)
                error_msg = f"MPFB Bridge returned error status during 'set_targets': {msg}"
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                return self._failed_apply(request, resp_fid, resp_display, error_msg)

            res_obj = response.get("result", {})
            if not isinstance(res_obj, dict) or not res_obj.get("performed", False):
                res_errors = res_obj.get("resolution_errors") if isinstance(res_obj, dict) else None
                self._execute_rollback(rollback_stack, sender)
                error_msg = f"MPFB Bridge did not commit target changes (performed=False). Resolution errors: {res_errors}"
                self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
                return self._failed_apply(request, resp_fid, resp_display, error_msg)

        # Step 9: Immediate Read-Back Verification (Post-Mutation)
        try:
            post_live = self.state_service.get_live_state("Human", include_assets=bool(validated_assets))
        except TypeError:
            post_live = self.state_service.get_live_state("Human")

        if not post_live.blender_available or post_live.source != "live_blender" or (target_fdefs and not post_live.features):
            self._execute_rollback(rollback_stack, sender)
            error_msg = (
                f"Post-mutation read-back failed: Could not read state after applying changes: "
                f"{post_live.error_details or 'Bridge disconnected'}."
            )
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=error_msg)
            return self._failed_apply(request, resp_fid, resp_display, error_msg)

        verification_failed = False
        verification_msg = ""

        # Verify every target feature reached expected value within 0.001
        for feat_item in batch_features:
            fid = feat_item.get("feature_id")
            fdef = target_fdefs.get(fid) or VERIFIED_ALLOWLIST.get(fid)
            post_target = post_live.features.get(fid)
            if not post_target:
                verification_failed = True
                verification_msg = f"Feature '{feat_item.get('display_name', fid)}' missing from post-mutation state."
                break

            if fdef and fdef.is_sided:
                applied_l = post_target.left_value
                applied_r = post_target.right_value
                target_l = feat_item.get("proposed_left_value")
                target_r = feat_item.get("proposed_right_value")

                if abs(applied_l - target_l) > 0.001 or abs(applied_r - target_r) > 0.001:
                    verification_failed = True
                    verification_msg = (
                        f"Target value mismatch for bilateral feature '{fdef.display_name}'. "
                        f"Expected (left: {target_l:+.2f}, right: {target_r:+.2f}), "
                        f"but observed (left: {applied_l:+.2f}, right: {applied_r:+.2f})."
                    )
                    break
            elif fdef:
                applied_v = post_target.value
                target_v = feat_item.get("proposed_value")
                if abs(applied_v - target_v) > 0.001:
                    verification_failed = True
                    verification_msg = (
                        f"Target value mismatch for feature '{fdef.display_name}'. "
                        f"Expected {target_v:+.2f}, but observed {applied_v:+.2f}."
                    )
                    break

        # Verify unrelated allowlisted features did NOT change
        if not verification_failed and target_fdefs:
            for other_fid, other_def in VERIFIED_ALLOWLIST.items():
                if other_fid not in target_fdefs and other_fid in pre_live.features and other_fid in post_live.features:
                    pre_f = pre_live.features[other_fid]
                    post_f = post_live.features[other_fid]
                    if other_def.is_sided:
                        if (abs(post_f.left_value - pre_f.left_value) > 0.001 or
                            abs(post_f.right_value - pre_f.right_value) > 0.001):
                            verification_failed = True
                            verification_msg = (
                                f"Unrelated bilateral feature '{other_def.display_name}' was unexpectedly modified. "
                                f"Was (left: {pre_f.left_value:+.2f}, right: {pre_f.right_value:+.2f}), "
                                f"now (left: {post_f.left_value:+.2f}, right: {post_f.right_value:+.2f})."
                            )
                            break
                    else:
                        if abs(post_f.value - pre_f.value) > 0.001:
                            verification_failed = True
                            verification_msg = (
                                f"Unrelated feature '{other_def.display_name}' was unexpectedly modified. "
                                f"Was {pre_f.value:+.2f}, now {post_f.value:+.2f}."
                            )
                            break

        # Verify equipped assets matched expected states
        if not verification_failed and validated_assets:
            for asset_item in validated_assets:
                atype = asset_item.get("asset_type")
                prop_frag = asset_item.get("proposed_fragment")
                if atype == "hair":
                    if prop_frag is None:
                        if post_live.equipped_hair is not None:
                            verification_failed = True
                            verification_msg = (
                                f"Expected character 'Human' to be bald, but hairstyle "
                                f"'{post_live.equipped_hair.asset_source}' ({post_live.equipped_hair.name}) is still equipped."
                            )
                            break
                    else:
                        if not post_live.equipped_hair:
                            verification_failed = True
                            verification_msg = (
                                f"Expected hairstyle '{prop_frag}' on character 'Human', but no hairstyle is equipped."
                            )
                            break
                        elif post_live.equipped_hair.asset_source != prop_frag:
                            verification_failed = True
                            verification_msg = (
                                f"Hairstyle mismatch on character 'Human'. Expected '{prop_frag}', "
                                f"but observed '{post_live.equipped_hair.asset_source}'."
                            )
                            break
                elif atype == "eyebrows":
                    if not post_live.equipped_eyebrows:
                        verification_failed = True
                        verification_msg = (
                            f"Expected eyebrows '{prop_frag}' on character 'Human', but no eyebrows are equipped."
                        )
                        break
                    elif post_live.equipped_eyebrows.asset_source != prop_frag:
                        verification_failed = True
                        verification_msg = (
                            f"Eyebrow mismatch on character 'Human'. Expected '{prop_frag}', "
                            f"but observed '{post_live.equipped_eyebrows.asset_source}'."
                        )
                        break

        if verification_failed:
            self._execute_rollback(rollback_stack, sender)
            full_verif_err = f"Post-mutation read-back verification failed: {verification_msg}"
            self.db.complete_preview_apply(request.preview_log_id, "FAILED", error_message=full_verif_err)
            log_id = self.db.log_request(
                request_text=f"Apply preview #{request.preview_log_id} to character Human",
                mode="live_apply",
                status="APPLY_FAILED",
                case_id=request.case_id,
                parsed_feature=resp_display,
                error_message=full_verif_err,
                details={
                    "preview_log_id": request.preview_log_id,
                    "applied_modifiers": validated_modifiers,
                    "applied_assets": applied_asset_records,
                    "verification_error": verification_msg
                }
            )
            return RefinementApplyResponse(
                status="APPLY_FAILED",
                apply_log_id=log_id,
                preview_log_id=request.preview_log_id,
                case_id=request.case_id,
                character_name="Human",
                feature_id=resp_fid,
                display_name=resp_display,
                previous_value=prev_val,
                left_previous_value=prev_left,
                right_previous_value=prev_right,
                verified=False,
                drift_checked=True,
                modifiers_applied=validated_modifiers if validated_modifiers else None,
                assets_applied=applied_asset_records if applied_asset_records else None,
                message=f"Refinement application failed verification: {full_verif_err}",
                error_message=full_verif_err
            )

        # Step 10: Complete Audit Logging & Success Confirmation
        features_applied: List[Dict[str, Any]] = []
        for feat_item in batch_features:
            fid = feat_item.get("feature_id")
            fdef = target_fdefs.get(fid) or VERIFIED_ALLOWLIST.get(fid)
            pre_f = pre_live.features.get(fid)
            post_f = post_live.features.get(fid)
            if fdef and fdef.is_sided:
                features_applied.append({
                    "feature_id": fid,
                    "display_name": fdef.display_name,
                    "is_sided": True,
                    "previous_left_value": pre_f.left_value if pre_f else None,
                    "previous_right_value": pre_f.right_value if pre_f else None,
                    "applied_left_value": post_f.left_value if post_f else None,
                    "applied_right_value": post_f.right_value if post_f else None,
                    "target_identifiers": feat_item.get("target_identifiers", []),
                    "verified": True
                })
            elif fdef:
                features_applied.append({
                    "feature_id": fid,
                    "display_name": fdef.display_name,
                    "is_sided": False,
                    "previous_value": pre_f.value if pre_f else None,
                    "applied_value": post_f.value if post_f else None,
                    "target_identifiers": feat_item.get("target_identifiers", []),
                    "verified": True
                })

        first_post = post_live.features.get(first_fdef.feature_id) if first_fdef and post_live.features else None
        applied_val = first_post.value if first_post and not first_fdef.is_sided else None
        applied_left = first_post.left_value if first_post and first_fdef.is_sided else None
        applied_right = first_post.right_value if first_post and first_fdef.is_sided else None

        if batch_features and applied_asset_records:
            names_str = ", ".join(f.get("display_name", "") for f in batch_features)
            asset_str = ", ".join(f"{a.get('asset_type')}: {a.get('display_name') or a.get('action')}" for a in applied_asset_records)
            success_msg = (
                f"Successfully applied and verified {len(batch_features)} facial adjustments [{names_str}] "
                f"and {len(applied_asset_records)} asset changes [{asset_str}] on character 'Human' in Blender. "
                f"Read-back confirmed all target values and equipped assets."
            )
        elif applied_asset_records:
            asset_str = ", ".join(f"{a.get('asset_type')}: {a.get('display_name') or a.get('action')}" for a in applied_asset_records)
            success_msg = (
                f"Successfully applied and verified {len(applied_asset_records)} asset changes [{asset_str}] "
                f"on character 'Human' in Blender. Read-back confirmed equipped assets."
            )
        elif is_multi:
            names_str = ", ".join(f.get("display_name", "") for f in batch_features)
            success_msg = (
                f"Successfully applied and verified {len(batch_features)} facial adjustments [{names_str}] "
                f"across {len(validated_modifiers)} morph targets on character 'Human' in Blender. "
                f"Read-back confirmed all target values and confirmed all unrelated features remained unchanged."
            )
        else:
            success_msg = (
                f"Successfully applied and verified changes to {first_fdef.display_name} on character 'Human' in Blender. "
                f"Read-back confirmed target values and confirmed all unrelated features remained unchanged."
            )

        target_cat = validated_modifiers[0]["category"] if validated_modifiers else (applied_asset_records[0].get("asset_type") if applied_asset_records else None)

        log_id = self.db.log_request(
            request_text=f"Apply preview #{request.preview_log_id} to character Human",
            mode="live_apply",
            status="APPLIED",
            case_id=request.case_id or preview_record.get("case_id"),
            parsed_feature=resp_display,
            target_identifier=target_cat,
            current_value=prev_val if prev_val is not None else prev_left,
            proposed_value=applied_val if applied_val is not None else applied_left,
            details={
                "preview_log_id": request.preview_log_id,
                "character_name": "Human",
                "is_multi_feature": is_multi,
                "feature_count": len(batch_features),
                "modifiers_applied": validated_modifiers,
                "features_applied": features_applied,
                "assets_applied": applied_asset_records,
                "previous_value": prev_val if not is_multi else None,
                "applied_value": applied_val if not is_multi else None,
                "left_previous_value": prev_left if not is_multi else None,
                "right_previous_value": prev_right if not is_multi else None,
                "left_applied_value": applied_left if not is_multi else None,
                "right_applied_value": applied_right if not is_multi else None,
                "drift_checked": True,
                "verified": True,
                "bridge_changes": res_obj.get("changes", [])
            }
        )

        self.db.complete_preview_apply(
            preview_log_id=request.preview_log_id,
            status="APPLIED",
            apply_log_id=log_id
        )

        return RefinementApplyResponse(
            status="APPLIED",
            apply_log_id=log_id,
            preview_log_id=request.preview_log_id,
            case_id=request.case_id or preview_record.get("case_id"),
            character_name="Human",
            feature_id=resp_fid,
            display_name=resp_display,
            previous_value=prev_val if not is_multi else None,
            applied_value=applied_val if not is_multi else None,
            left_previous_value=prev_left if not is_multi else None,
            right_previous_value=prev_right if not is_multi else None,
            left_applied_value=applied_left if not is_multi else None,
            right_applied_value=applied_right if not is_multi else None,
            verified=True,
            drift_checked=True,
            modifiers_applied=validated_modifiers if validated_modifiers else None,
            features_applied=features_applied if features_applied else None,
            assets_applied=applied_asset_records if applied_asset_records else None,
            message=success_msg,
            error_message=None
        )

