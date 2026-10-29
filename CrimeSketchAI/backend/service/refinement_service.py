"""
Refinement Service for CrimeSketchAI.

Coordinates parsing, slider value validation, range boundary clamping,
payload construction, and SQLite logging in dry-run mode.
Supports single-feature instructions and multi-feature composite witness descriptions.

State Handling Policy:
- Offline dry-run only: NEVER invokes mpfb_set_targets or mutation commands.
- Cached reference mode (default, use_live_state=False): Uses verified baseline values.
- Live Blender mode (use_live_state=True): Queries live target stack via BlenderStateService.
- Zero fallback: If live read fails when use_live_state=True, the preview is rejected;
  cached reference values are NEVER silently substituted.
- Bilateral features: Reads left and right values independently, preserves asymmetry,
  and validates/clamps each side individually.
- Client-asserted `current_value` is strictly forbidden and rejected.
- Dual Parser Architecture: Supports verified rule-based parser (default) and
  local Ollama AI parser (qwen3:4b), selectable per-request or via environment.
- Strict no-silent-fallback on AI mode: If user selects AI mode, failure is rejected
  with exact diagnostic details, never silently masked.
- Multi-feature batch integrity: Validates every feature independently against VERIFIED_ALLOWLIST.
  Rejects whole batch if any feature is invalid or ambiguous.
"""

from typing import Optional, Dict, Any, List
from backend.config import settings
from backend.parser.refinement_parser import RefinementParser, ParseError, ParsedRefinement
from backend.parser.ollama_parser import OllamaRefinementParser
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST, FeatureDefinition
from backend.storage.database import Database
from backend.service.blender_state_service import BlenderStateService
from backend.models.schemas import (
    RefinementRequest,
    RefinementResponse,
    ProposedPayload,
    ProposedModifier,
    LiveStateResponse,
    FeatureAdjustmentPreview,
    AssetAdjustmentPreview,
    EquippedAssetInfo
)
from backend.parser.asset_catalog import (
    HAIRSTYLE_CATALOG,
    EYEBROW_CATALOG,
    get_asset_by_fragment
)


class RefinementService:
    def __init__(
        self,
        db: Optional[Database] = None,
        state_service: Optional[BlenderStateService] = None,
        ai_parser: Optional[OllamaRefinementParser] = None,
        default_parser_mode: Optional[str] = None
    ):
        self.db = db or Database()
        self.state_service = state_service or BlenderStateService()
        self.rule_parser = RefinementParser()
        self.ai_parser = ai_parser or OllamaRefinementParser()
        self.default_parser_mode = default_parser_mode or settings.PARSER_MODE

    def _resolve_parser(self, requested_mode: Optional[str]):
        """Resolves which parser instance and metadata to use."""
        mode = requested_mode or self.default_parser_mode
        if mode in ("ai", "ollama"):
            return self.ai_parser, "ai", settings.OLLAMA_MODEL
        return self.rule_parser, "rule_based", None

    def process_dry_run(self, request: RefinementRequest) -> RefinementResponse:
        """
        Processes a natural language refinement command or multi-feature description.
        Generates a verified dry-run preview without mutating the Blender 3D scene.
        """
        active_parser, active_parser_mode, active_model = self._resolve_parser(request.parser_mode)

        # Character name sanitization
        raw_char_name = (request.character_name or "").strip()
        character_name = raw_char_name if raw_char_name else "Human"

        # Step 1: Rejection of caller-supplied current_value
        if request.current_value is not None:
            error_msg = (
                "Caller-supplied 'current_value' is rejected. Forbidden: 'current_value' was supplied in the request body. "
                "Clients cannot assert or override 3D model state. "
                "Values are determined strictly from verified offline reference data or live Blender inspection."
            )
            log_id = self.db.log_request(
                request_text=request.text,
                mode="dry_run",
                status="REJECTED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "use_live_state": request.use_live_state,
                    "parser_mode": active_parser_mode,
                    "parser_model": active_model,
                    "value_source": "live_blender" if request.use_live_state else "cached_reference",
                    "rejected_caller_value": request.current_value
                }
            )
            return RefinementResponse(
                status="REJECTED",
                mode="dry_run",
                case_id=request.case_id,
                input_text=request.text,
                parser_mode=active_parser_mode,
                parser_model=active_model,
                message=f"Refinement rejected: {error_msg}",
                error_message=error_msg,
                log_id=log_id
            )

        # Step 2: Parse the natural language instruction
        try:
            parsed: ParsedRefinement = active_parser.parse(request.text)
        except ParseError as e:
            error_msg = str(e)
            log_id = self.db.log_request(
                request_text=request.text,
                mode="dry_run",
                status="REJECTED",
                case_id=request.case_id,
                error_message=error_msg,
                details={
                    "use_live_state": request.use_live_state,
                    "parser_mode": active_parser_mode,
                    "parser_model": active_model,
                    "value_source": "live_blender" if request.use_live_state else "cached_reference"
                }
            )
            return RefinementResponse(
                status="REJECTED",
                mode="dry_run",
                case_id=request.case_id,
                input_text=request.text,
                parser_mode=active_parser_mode,
                parser_model=active_model,
                message=f"Refinement rejected: {error_msg}",
                error_message=error_msg,
                log_id=log_id
            )

        # Extract all feature adjustments and asset adjustments from parsed output
        raw_asset_adjs = parsed.asset_adjustments if hasattr(parsed, 'asset_adjustments') and parsed.asset_adjustments else []
        if getattr(parsed, 'feature_id', None) == "asset_customization":
            feature_items: List[ParsedRefinement] = []
        else:
            feature_items: List[ParsedRefinement] = (
                parsed.features if hasattr(parsed, 'features') and parsed.features else [parsed]
            )
        is_multi = len(feature_items) > 1

        # Step 3: Handle State Resolution (Live Blender vs Cached Reference)
        live_resp: Optional[LiveStateResponse] = None
        if request.use_live_state:
            try:
                live_resp = self.state_service.get_live_state(character_name, include_assets=bool(raw_asset_adjs))
            except TypeError:
                live_resp = self.state_service.get_live_state(character_name)

            if not live_resp.blender_available or live_resp.source != "live_blender" or (feature_items and not live_resp.features):
                error_msg = (
                    f"Live Blender state unavailable: {live_resp.error_details or 'Could not read target stack from Blender'}. "
                    "Preview rejected because use_live_state=True and live state cannot be verified."
                )
                log_id = self.db.log_request(
                    request_text=request.text,
                    mode="dry_run",
                    status="REJECTED",
                    case_id=request.case_id,
                    parsed_feature="asset_customization" if not feature_items else ("multi_feature" if is_multi else feature_items[0].display_name),
                    error_message=error_msg,
                    details={
                        "use_live_state": True,
                        "parser_mode": active_parser_mode,
                        "parser_model": active_model,
                        "state_source": live_resp.source,
                        "value_source": live_resp.source,
                        "is_live_blender_value": False,
                        "blender_available": live_resp.blender_available,
                        "error_details": live_resp.error_details
                    }
                )
                return RefinementResponse(
                    status="REJECTED",
                    mode="dry_run",
                    case_id=request.case_id,
                    input_text=request.text,
                    feature_id="asset_customization" if not feature_items else ("multi_feature" if is_multi else feature_items[0].feature_id),
                    display_name="Hair / Eyebrow Customization" if not feature_items else (f"Multi-Feature Batch ({len(feature_items)} features)" if is_multi else feature_items[0].display_name),
                    parser_mode=active_parser_mode,
                    parser_model=active_model,
                    value_source=live_resp.source,
                    is_live_blender_value=False,
                    reference_note="Live Blender state read failed; cached reference values were NOT substituted.",
                    message=f"Refinement rejected: {error_msg}",
                    error_message=error_msg,
                    log_id=log_id
                )

            # Check that every single requested feature exists in the live state
            for item in feature_items:
                if item.feature_id not in live_resp.features:
                    error_msg = (
                        f"Live Blender target state missing for feature '{item.display_name}' ({item.feature_id}). "
                        "Preview rejected because use_live_state=True."
                    )
                    log_id = self.db.log_request(
                        request_text=request.text,
                        mode="dry_run",
                        status="REJECTED",
                        case_id=request.case_id,
                        parsed_feature=item.display_name,
                        error_message=error_msg,
                        details={
                            "use_live_state": True,
                            "parser_mode": active_parser_mode,
                            "parser_model": active_model,
                            "state_source": "live_blender",
                            "value_source": "live_blender"
                        }
                    )
                    return RefinementResponse(
                        status="REJECTED",
                        mode="dry_run",
                        case_id=request.case_id,
                        input_text=request.text,
                        feature_id=item.feature_id,
                        display_name=item.display_name,
                        parser_mode=active_parser_mode,
                        parser_model=active_model,
                        value_source="live_blender",
                        is_live_blender_value=False,
                        message=f"Refinement rejected: {error_msg}",
                        error_message=error_msg,
                        log_id=log_id
                    )

        # Step 3b: Resolve baseline and proposed asset adjustments
        asset_previews: List[AssetAdjustmentPreview] = []
        value_source = "live_blender" if request.use_live_state else "cached_reference"
        is_live_blender = request.use_live_state is True

        live_hair = getattr(live_resp, 'equipped_hair', None) if (request.use_live_state and live_resp) else None
        live_eb = getattr(live_resp, 'equipped_eyebrows', None) if (request.use_live_state and live_resp) else None

        if request.use_live_state:
            curr_hair = live_hair
            curr_eb = live_eb
        else:
            curr_hair = EquippedAssetInfo(
                name=f"{character_name}.short01",
                object_type="Hair",
                asset_source="short01/short01.mhclo",
                asset_id="short01",
                in_current_scene=True
            )
            curr_eb = EquippedAssetInfo(
                name=f"{character_name}.eyebrow003",
                object_type="Eyebrows",
                asset_source="eyebrow003/eyebrow003.mhclo",
                asset_id="eyebrow003",
                in_current_scene=True
            )

        for adj in raw_asset_adjs:
            if adj.asset_type == "hair":
                cur_id = curr_hair.asset_id if curr_hair else "bald"
                cur_name = curr_hair.name if curr_hair else None
                cur_frag = curr_hair.asset_source if curr_hair else None
                prop_id = adj.asset_id
                prop_frag = adj.fragment
                prop_disp = adj.display_name
                if prop_id == "bald":
                    action = "remove" if cur_id != "bald" else "keep"
                elif cur_id == prop_id:
                    action = "keep"
                elif cur_id == "bald":
                    action = "add"
                else:
                    action = "swap"
                asset_previews.append(AssetAdjustmentPreview(
                    asset_type="hair",
                    action=action,
                    current_asset_id=cur_id,
                    current_asset_name=cur_name,
                    current_fragment=cur_frag,
                    proposed_asset_id=prop_id,
                    proposed_display_name=prop_disp,
                    proposed_fragment=prop_frag
                ))
            elif adj.asset_type == "eyebrows":
                cur_id = curr_eb.asset_id if curr_eb else None
                cur_name = curr_eb.name if curr_eb else None
                cur_frag = curr_eb.asset_source if curr_eb else None
                prop_id = adj.asset_id
                prop_frag = adj.fragment
                prop_disp = adj.display_name
                if cur_id == prop_id:
                    action = "keep"
                elif cur_id is None or cur_id == "none":
                    action = "add"
                else:
                    action = "swap"
                asset_previews.append(AssetAdjustmentPreview(
                    asset_type="eyebrows",
                    action=action,
                    current_asset_id=cur_id,
                    current_asset_name=cur_name,
                    current_fragment=cur_frag,
                    proposed_asset_id=prop_id,
                    proposed_display_name=prop_disp,
                    proposed_fragment=prop_frag
                ))

        # Baseline snapshot for allowlisted features
        baseline_snapshot = None
        if request.use_live_state and live_resp and live_resp.features:
            baseline_snapshot = {
                fid: {
                    "value": fstate.value,
                    "left_value": fstate.left_value,
                    "right_value": fstate.right_value,
                    "is_symmetric": fstate.is_symmetric
                }
                for fid, fstate in live_resp.features.items()
            }

        # Case A: Asset-only customization (0 geometry adjustments)
        if not feature_items and asset_previews:
            proposed_payload = ProposedPayload(
                name=character_name,
                modifiers=[],
                symmetry=False,
                prune=True,
                refit=False
            )
            asset_descriptions = []
            for ap in asset_previews:
                if ap.proposed_asset_id == "bald":
                    asset_descriptions.append(f"Hair: {ap.current_asset_id or 'none'} -> Bald (remove)")
                else:
                    cur_desc = ap.current_asset_id or "none"
                    asset_descriptions.append(f"{ap.asset_type.capitalize()}: {cur_desc} -> {ap.proposed_display_name}")

            preview_msg = (
                f"Live dry-run preview: Proposed asset customization [{', '.join(asset_descriptions)}] "
                f"on character '{character_name}'. (Data source: {value_source})."
            )

            ref_note = (
                f"Observed from live Blender model '{character_name}'; NOT cached reference."
                if is_live_blender
                else "Value is an offline cached reference value from the verified baseline; this is NOT a live Blender socket read."
            )

            log_id = self.db.log_request(
                request_text=request.text,
                mode="dry_run",
                status="PREVIEW_READY",
                case_id=request.case_id,
                parsed_feature="asset_customization",
                target_identifier="asset:customization",
                details={
                    "use_live_state": request.use_live_state,
                    "parser_mode": active_parser_mode,
                    "parser_model": active_model,
                    "value_source": value_source,
                    "is_live_blender_value": is_live_blender,
                    "is_multi_feature": False,
                    "is_asset_customization": True,
                    "feature_count": 0,
                    "features": [],
                    "asset_adjustments": [a.model_dump() for a in asset_previews],
                    "equipped_hair": curr_hair.model_dump() if curr_hair else None,
                    "equipped_eyebrows": curr_eb.model_dump() if curr_eb else None,
                    "live_baseline_snapshot": baseline_snapshot,
                    "proposed_payload": proposed_payload.model_dump()
                }
            )

            return RefinementResponse(
                status="PREVIEW_READY",
                mode="dry_run",
                case_id=request.case_id,
                input_text=request.text,
                feature_id="asset_customization",
                display_name="Hair / Eyebrow Customization",
                parser_mode=active_parser_mode,
                parser_model=active_model,
                value_source=value_source,
                is_live_blender_value=is_live_blender,
                reference_note=ref_note,
                target_identifier="asset:customization",
                target_identifiers=[],
                target_shapekeys=[],
                proposed_payload=proposed_payload,
                features=[],
                asset_adjustments=asset_previews,
                message=preview_msg,
                log_id=log_id
            )

        # Step 4: Process every feature adjustment in the batch
        all_modifiers: List[ProposedModifier] = []
        all_target_ids: List[str] = []
        all_shapekeys: List[str] = []
        feature_previews: List[FeatureAdjustmentPreview] = []
        features_detail_for_db: List[Dict[str, Any]] = []

        for item in feature_items:
            fdef: FeatureDefinition = VERIFIED_ALLOWLIST[item.feature_id]
            shapekeys = list(fdef.positive_targets if item.direction > 0 else fdef.negative_targets)
            all_shapekeys.extend(shapekeys)

            if request.use_live_state:
                live_feat = live_resp.features[item.feature_id]

                if fdef.is_sided:
                    if live_feat.left_value is None or live_feat.right_value is None:
                        error_msg = f"Live target values for bilateral feature '{fdef.display_name}' are incomplete."
                        log_id = self.db.log_request(
                            request_text=request.text,
                            mode="dry_run",
                            status="REJECTED",
                            case_id=request.case_id,
                            parsed_feature=fdef.display_name,
                            error_message=error_msg
                        )
                        return RefinementResponse(
                            status="REJECTED",
                            mode="dry_run",
                            case_id=request.case_id,
                            input_text=request.text,
                            message=f"Refinement rejected: {error_msg}",
                            error_message=error_msg,
                            log_id=log_id
                        )

                    left_cur = live_feat.left_value
                    right_cur = live_feat.right_value
                    is_sym = abs(left_cur - right_cur) < 1e-4

                    raw_left_prop = left_cur + item.delta
                    raw_right_prop = right_cur + item.delta

                    left_clamped = False
                    if raw_left_prop > fdef.max_value:
                        left_prop = fdef.max_value
                        left_clamped = True
                    elif raw_left_prop < fdef.min_value:
                        left_prop = fdef.min_value
                        left_clamped = True
                    else:
                        left_prop = round(raw_left_prop, 4)

                    right_clamped = False
                    if raw_right_prop > fdef.max_value:
                        right_prop = fdef.max_value
                        right_clamped = True
                    elif raw_right_prop < fdef.min_value:
                        right_prop = fdef.min_value
                        right_clamped = True
                    else:
                        right_prop = round(raw_right_prop, 4)

                    is_clamped = left_clamped or right_clamped
                    warnings = []
                    if left_clamped:
                        warnings.append(
                            f"Left proposed adjustment reaches slider limit ({'+' if fdef.max_value >= 0 else ''}{fdef.max_value:.1f}) "
                            f"for {fdef.display_name}. Clamped to {left_prop}."
                        )
                    if right_clamped:
                        warnings.append(
                            f"Right proposed adjustment reaches slider limit ({'+' if fdef.max_value >= 0 else ''}{fdef.max_value:.1f}) "
                            f"for {fdef.display_name}. Clamped to {right_prop}."
                        )
                    boundary_warning = " ".join(warnings) if warnings else None

                    item_tids = [
                        f"{fdef.section}:{fdef.category}:left",
                        f"{fdef.section}:{fdef.category}:right"
                    ]
                    all_target_ids.extend(item_tids)

                    all_modifiers.append(ProposedModifier(
                        section=fdef.section,
                        category=fdef.category,
                        side="left",
                        value=left_prop
                    ))
                    all_modifiers.append(ProposedModifier(
                        section=fdef.section,
                        category=fdef.category,
                        side="right",
                        value=right_prop
                    ))

                    feat_prev = FeatureAdjustmentPreview(
                        feature_id=fdef.feature_id,
                        display_name=fdef.display_name,
                        section=fdef.section,
                        category=fdef.category,
                        is_sided=True,
                        side="left,right",
                        direction=item.direction,
                        magnitude=item.magnitude,
                        adjustment_delta=item.delta,
                        current_value=left_cur,
                        proposed_value=left_prop,
                        left_current_value=left_cur,
                        right_current_value=right_cur,
                        left_proposed_value=left_prop,
                        right_proposed_value=right_prop,
                        is_symmetric=is_sym,
                        is_boundary_clamped=is_clamped,
                        boundary_warning=boundary_warning,
                        target_identifiers=item_tids,
                        target_shapekeys=shapekeys
                    )
                    feature_previews.append(feat_prev)

                    features_detail_for_db.append({
                        "feature_id": fdef.feature_id,
                        "display_name": fdef.display_name,
                        "is_sided": True,
                        "observed_current_value": left_cur,
                        "proposed_value": left_prop,
                        "observed_left_value": left_cur,
                        "observed_right_value": right_cur,
                        "proposed_left_value": left_prop,
                        "proposed_right_value": right_prop,
                        "adjustment_delta": item.delta,
                        "is_boundary_clamped": is_clamped,
                        "boundary_warning": boundary_warning,
                        "target_identifiers": item_tids,
                        "target_shapekeys": shapekeys
                    })

                else:
                    # Unsided live
                    if live_feat.value is None:
                        error_msg = f"Live target value for feature '{fdef.display_name}' is missing."
                        log_id = self.db.log_request(
                            request_text=request.text,
                            mode="dry_run",
                            status="REJECTED",
                            case_id=request.case_id,
                            parsed_feature=fdef.display_name,
                            error_message=error_msg
                        )
                        return RefinementResponse(
                            status="REJECTED",
                            mode="dry_run",
                            case_id=request.case_id,
                            input_text=request.text,
                            message=f"Refinement rejected: {error_msg}",
                            error_message=error_msg,
                            log_id=log_id
                        )

                    cur_val = live_feat.value
                    raw_prop = cur_val + item.delta

                    is_clamped = False
                    boundary_warning = None
                    if raw_prop > fdef.max_value:
                        prop_val = fdef.max_value
                        is_clamped = True
                        boundary_warning = (
                            f"Proposed value {raw_prop:+.2f} for {fdef.display_name} "
                            f"reaches the maximum slider limit (+{fdef.max_value:.1f}). Clamped to {prop_val}."
                        )
                    elif raw_prop < fdef.min_value:
                        prop_val = fdef.min_value
                        is_clamped = True
                        boundary_warning = (
                            f"Proposed value {raw_prop:+.2f} for {fdef.display_name} "
                            f"reaches the minimum slider limit ({fdef.min_value:.1f}). Clamped to {prop_val}."
                        )
                    else:
                        prop_val = round(raw_prop, 4)

                    item_tids = [f"{fdef.section}:{fdef.category}:unsided"]
                    all_target_ids.extend(item_tids)

                    all_modifiers.append(ProposedModifier(
                        section=fdef.section,
                        category=fdef.category,
                        side="unsided",
                        value=prop_val
                    ))

                    feat_prev = FeatureAdjustmentPreview(
                        feature_id=fdef.feature_id,
                        display_name=fdef.display_name,
                        section=fdef.section,
                        category=fdef.category,
                        is_sided=False,
                        side="unsided",
                        direction=item.direction,
                        magnitude=item.magnitude,
                        adjustment_delta=item.delta,
                        current_value=cur_val,
                        proposed_value=prop_val,
                        is_boundary_clamped=is_clamped,
                        boundary_warning=boundary_warning,
                        target_identifiers=item_tids,
                        target_shapekeys=shapekeys
                    )
                    feature_previews.append(feat_prev)

                    features_detail_for_db.append({
                        "feature_id": fdef.feature_id,
                        "display_name": fdef.display_name,
                        "is_sided": False,
                        "observed_current_value": cur_val,
                        "proposed_value": prop_val,
                        "adjustment_delta": item.delta,
                        "is_boundary_clamped": is_clamped,
                        "boundary_warning": boundary_warning,
                        "target_identifiers": item_tids,
                        "target_shapekeys": shapekeys
                    })

            else:
                # use_live_state=False: Cached reference baseline mode
                ref_val = fdef.reference_value
                raw_prop = ref_val + item.delta

                is_clamped = False
                boundary_warning = None
                if raw_prop > fdef.max_value:
                    prop_val = fdef.max_value
                    is_clamped = True
                    boundary_warning = (
                        f"Proposed value {raw_prop:+.2f} for {fdef.display_name} "
                        f"reaches the maximum slider limit (+{fdef.max_value:.1f}). Clamped to {prop_val}."
                    )
                elif raw_prop < fdef.min_value:
                    prop_val = fdef.min_value
                    is_clamped = True
                    boundary_warning = (
                        f"Proposed value {raw_prop:+.2f} for {fdef.display_name} "
                        f"reaches the minimum slider limit ({fdef.min_value:.1f}). Clamped to {prop_val}."
                    )
                else:
                    prop_val = round(raw_prop, 4)

                if fdef.is_sided:
                    item_tids = [
                        f"{fdef.section}:{fdef.category}:left",
                        f"{fdef.section}:{fdef.category}:right"
                    ]
                    all_target_ids.extend(item_tids)
                    for s in fdef.sides:
                        all_modifiers.append(ProposedModifier(
                            section=fdef.section,
                            category=fdef.category,
                            side=s,
                            value=prop_val
                        ))

                    feat_prev = FeatureAdjustmentPreview(
                        feature_id=fdef.feature_id,
                        display_name=fdef.display_name,
                        section=fdef.section,
                        category=fdef.category,
                        is_sided=True,
                        side="left,right",
                        direction=item.direction,
                        magnitude=item.magnitude,
                        adjustment_delta=item.delta,
                        current_value=ref_val,
                        proposed_value=prop_val,
                        left_current_value=ref_val,
                        right_current_value=ref_val,
                        left_proposed_value=prop_val,
                        right_proposed_value=prop_val,
                        is_symmetric=True,
                        is_boundary_clamped=is_clamped,
                        boundary_warning=boundary_warning,
                        target_identifiers=item_tids,
                        target_shapekeys=shapekeys
                    )
                    feature_previews.append(feat_prev)

                    features_detail_for_db.append({
                        "feature_id": fdef.feature_id,
                        "display_name": fdef.display_name,
                        "is_sided": True,
                        "observed_current_value": ref_val,
                        "proposed_value": prop_val,
                        "observed_left_value": ref_val,
                        "observed_right_value": ref_val,
                        "proposed_left_value": prop_val,
                        "proposed_right_value": prop_val,
                        "adjustment_delta": item.delta,
                        "is_boundary_clamped": is_clamped,
                        "boundary_warning": boundary_warning,
                        "target_identifiers": item_tids,
                        "target_shapekeys": shapekeys
                    })

                else:
                    item_tids = [f"{fdef.section}:{fdef.category}:unsided"]
                    all_target_ids.extend(item_tids)
                    all_modifiers.append(ProposedModifier(
                        section=fdef.section,
                        category=fdef.category,
                        side="unsided",
                        value=prop_val
                    ))

                    feat_prev = FeatureAdjustmentPreview(
                        feature_id=fdef.feature_id,
                        display_name=fdef.display_name,
                        section=fdef.section,
                        category=fdef.category,
                        is_sided=False,
                        side="unsided",
                        direction=item.direction,
                        magnitude=item.magnitude,
                        adjustment_delta=item.delta,
                        current_value=ref_val,
                        proposed_value=prop_val,
                        is_boundary_clamped=is_clamped,
                        boundary_warning=boundary_warning,
                        target_identifiers=item_tids,
                        target_shapekeys=shapekeys
                    )
                    feature_previews.append(feat_prev)

                    features_detail_for_db.append({
                        "feature_id": fdef.feature_id,
                        "display_name": fdef.display_name,
                        "is_sided": False,
                        "observed_current_value": ref_val,
                        "proposed_value": prop_val,
                        "adjustment_delta": item.delta,
                        "is_boundary_clamped": is_clamped,
                        "boundary_warning": boundary_warning,
                        "target_identifiers": item_tids,
                        "target_shapekeys": shapekeys
                    })

        # Step 5: Construct proposed payload (dry-run preview only)
        proposed_payload = ProposedPayload(
            name=character_name,
            modifiers=all_modifiers,
            symmetry=False,
            prune=True,
            refit=False
        )

        # Baseline snapshot for all 10 allowlisted features
        baseline_snapshot = None
        if request.use_live_state and live_resp and live_resp.features:
            baseline_snapshot = {
                fid: {
                    "value": fstate.value,
                    "left_value": fstate.left_value,
                    "right_value": fstate.right_value,
                    "is_symmetric": fstate.is_symmetric
                }
                for fid, fstate in live_resp.features.items()
            }

        # Step 6: Log audit trail to SQLite
        first_detail = features_detail_for_db[0]
        first_prev = feature_previews[0]
        first_fdef = VERIFIED_ALLOWLIST[feature_items[0].feature_id]

        if is_multi:
            feature_names = [p.display_name for p in feature_previews]
            preview_message = (
                f"Live dry-run preview: {len(feature_items)} facial adjustments proposed "
                f"[{', '.join(feature_names)}] across {len(all_modifiers)} morph targets "
                f"on character '{character_name}'. (Data source: {value_source})."
            )
        else:
            dir_word = "increased" if feature_items[0].direction > 0 else "decreased"
            if request.use_live_state:
                if first_fdef.is_sided:
                    if first_prev.is_symmetric:
                        preview_message = (
                            f"Live dry-run preview: {first_fdef.display_name} will be {dir_word} by {abs(feature_items[0].delta):+.2f} "
                            f"from live Blender value {first_prev.left_current_value:+.2f} (symmetric) to proposed {first_prev.left_proposed_value:+.2f} "
                            f"across target(s) [{', '.join(first_prev.target_identifiers)}] on character '{character_name}'. (Data source: live Blender target stack)."
                        )
                    else:
                        diff = first_prev.right_current_value - first_prev.left_current_value
                        preview_message = (
                            f"Live dry-run preview: {first_fdef.display_name} will be {dir_word} by {abs(feature_items[0].delta):+.2f} "
                            f"from live Blender asymmetric values (left: {first_prev.left_current_value:+.2f}, right: {first_prev.right_current_value:+.2f}, diff: {diff:+.2f}) "
                            f"to proposed (left: {first_prev.left_proposed_value:+.2f}, right: {first_prev.right_proposed_value:+.2f}) "
                            f"across target(s) [{', '.join(first_prev.target_identifiers)}] on character '{character_name}'. Preserved bilateral asymmetry."
                        )
                else:
                    preview_message = (
                        f"Live dry-run preview: {first_fdef.display_name} will be {dir_word} by {abs(feature_items[0].delta):+.2f} "
                        f"from live Blender value {first_prev.current_value:+.2f} to proposed {first_prev.proposed_value:+.2f} "
                        f"across target(s) [{first_prev.target_identifiers[0]}] on character '{character_name}'. (Data source: live Blender target stack)."
                    )
            else:
                targets_str = ", ".join(first_prev.target_identifiers)
                preview_message = (
                    f"Dry-run preview: {first_fdef.display_name} will be {dir_word} by {abs(feature_items[0].delta):+.2f} "
                    f"from cached reference {first_fdef.reference_value:+.2f} to proposed {first_prev.proposed_value:+.2f} "
                    f"across target(s) [{targets_str}] on character '{character_name}'. "
                    f"(Note: Uses offline cached reference value, NOT a live Blender read)."
                )
            if first_prev.boundary_warning:
                preview_message += f" Notice: {first_prev.boundary_warning}"

        if asset_previews:
            asset_descs = [f"{a.asset_type.capitalize()}: {a.current_asset_id or 'none'} -> {a.proposed_display_name}" for a in asset_previews]
            preview_message = f"{preview_message} Asset changes: [{', '.join(asset_descs)}]."

        ref_note = (
            f"Observed from live Blender model '{character_name}' target stack; NOT cached reference."
            if is_live_blender
            else "Value is an offline cached reference value from the verified baseline; this is NOT a live Blender socket read."
        )

        log_id = self.db.log_request(
            request_text=request.text,
            mode="dry_run",
            status="PREVIEW_READY",
            case_id=request.case_id,
            parsed_feature="multi_feature" if is_multi else first_fdef.display_name,
            target_identifier=all_target_ids[0],
            current_value=first_detail.get("observed_current_value") if not first_fdef.is_sided else first_detail.get("observed_left_value"),
            proposed_delta=round(sum(it.delta for it in feature_items), 4) if is_multi else feature_items[0].delta,
            proposed_value=first_detail.get("proposed_value") if not first_fdef.is_sided else first_detail.get("proposed_left_value"),
            details={
                "use_live_state": request.use_live_state,
                "parser_mode": active_parser_mode,
                "parser_model": active_model,
                "value_source": value_source,
                "is_live_blender_value": is_live_blender,
                "is_multi_feature": is_multi,
                "feature_count": len(feature_items),
                "features": features_detail_for_db,
                "asset_adjustments": [a.model_dump() for a in asset_previews] if asset_previews else None,
                "equipped_hair": curr_hair.model_dump() if curr_hair else None,
                "equipped_eyebrows": curr_eb.model_dump() if curr_eb else None,
                "observed_current_value": first_detail.get("observed_current_value"),
                "observed_left_value": first_detail.get("observed_left_value"),
                "observed_right_value": first_detail.get("observed_right_value"),
                "proposed_value": first_detail.get("proposed_value"),
                "proposed_left_value": first_detail.get("proposed_left_value"),
                "proposed_right_value": first_detail.get("proposed_right_value"),
                "is_symmetric": first_prev.is_symmetric,
                "is_boundary_clamped": any(p.is_boundary_clamped for p in feature_previews),
                "boundary_warning": " ".join([p.boundary_warning for p in feature_previews if p.boundary_warning]) or None,
                "target_identifiers": all_target_ids,
                "target_shapekeys": all_shapekeys,
                "live_baseline_snapshot": baseline_snapshot,
                "proposed_payload": proposed_payload.model_dump()
            }
        )

        return RefinementResponse(
            status="PREVIEW_READY",
            mode="dry_run",
            case_id=request.case_id,
            input_text=request.text,
            feature_id="multi_feature" if is_multi else first_fdef.feature_id,
            display_name=f"Multi-Feature Batch ({len(feature_items)} features)" if is_multi else first_fdef.display_name,
            parser_mode=active_parser_mode,
            parser_model=active_model,
            reference_value=(
                (first_detail.get("observed_current_value") if not first_fdef.is_sided else first_detail.get("observed_left_value"))
                if request.use_live_state
                else first_fdef.reference_value
            ) if not is_multi else None,
            current_value=first_detail.get("observed_current_value") if not first_fdef.is_sided else first_detail.get("observed_left_value"),
            value_source=value_source,
            is_live_blender_value=is_live_blender,
            reference_note=ref_note,
            left_current_value=first_detail.get("observed_left_value"),
            right_current_value=first_detail.get("observed_right_value"),
            left_proposed_value=first_detail.get("proposed_left_value"),
            right_proposed_value=first_detail.get("proposed_right_value"),
            is_symmetric=first_prev.is_symmetric,
            adjustment_delta=feature_items[0].delta if not is_multi else round(sum(it.delta for it in feature_items), 4),
            proposed_delta=feature_items[0].delta if not is_multi else round(sum(it.delta for it in feature_items), 4),
            proposed_value=first_detail.get("proposed_value") if not first_fdef.is_sided else first_detail.get("proposed_left_value"),
            is_boundary_clamped=any(p.is_boundary_clamped for p in feature_previews),
            boundary_warning=" ".join([p.boundary_warning for p in feature_previews if p.boundary_warning]) or None,
            target_identifier=all_target_ids[0],
            target_identifiers=all_target_ids,
            target_shapekeys=all_shapekeys,
            proposed_payload=proposed_payload,
            features=feature_previews,
            asset_adjustments=asset_previews if asset_previews else None,
            message=preview_message,
            log_id=log_id
        )
