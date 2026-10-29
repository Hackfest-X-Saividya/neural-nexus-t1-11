"""
Pydantic Schemas for CrimeSketchAI API.

Hardened schemas emphasizing dry-run offline state, cached reference values,
strict rejection of client-asserted Blender values, and live-state read schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RefinementRequest(BaseModel):
    text: str = Field(..., description="Natural language refinement command (e.g. 'Make the nose slightly wider.')")
    case_id: Optional[str] = Field(None, description="Optional case identifier for investigation tracking")
    character_name: Optional[str] = Field("Human", description="Name of the 3D character in Blender (default: Human)")
    use_live_state: bool = Field(
        False,
        description="Whether to query live target values from Blender. Defaults to False (offline cached reference mode)."
    )
    parser_mode: Optional[str] = Field(
        None,
        description="Parser mode: 'rule_based' (default) or 'ai' / 'ollama'. If omitted, defaults to backend configuration."
    )
    current_value: Optional[Any] = Field(
        None,
        description="FORBIDDEN: A client cannot assert or override Blender model state. Supplying this field will result in request rejection."
    )

class ProposedModifier(BaseModel):
    section: str
    category: str
    side: str
    value: float

class ProposedPayload(BaseModel):
    name: str
    modifiers: List[ProposedModifier]
    symmetry: bool
    prune: bool
    refit: bool

class FeatureAdjustmentPreview(BaseModel):
    feature_id: str = Field(..., description="Allowlisted feature ID")
    display_name: str = Field(..., description="Human-readable feature name")
    section: str
    category: str
    is_sided: bool
    side: str
    direction: int
    magnitude: float
    adjustment_delta: float
    current_value: Optional[float] = None
    proposed_value: Optional[float] = None
    left_current_value: Optional[float] = None
    right_current_value: Optional[float] = None
    left_proposed_value: Optional[float] = None
    right_proposed_value: Optional[float] = None
    is_symmetric: Optional[bool] = None
    is_boundary_clamped: bool = False
    boundary_warning: Optional[str] = None
    target_identifiers: List[str] = Field(default_factory=list)
    target_shapekeys: List[str] = Field(default_factory=list)

class AssetAdjustmentPreview(BaseModel):
    asset_type: str = Field(..., description="Asset type: 'hair' or 'eyebrows'")
    action: str = Field(..., description="Action: 'swap', 'remove', 'add', or 'keep'")
    current_asset_id: Optional[str] = Field(None, description="Currently equipped asset ID")
    current_asset_name: Optional[str] = Field(None, description="Blender object name of current asset (e.g. 'Human.short01')")
    current_fragment: Optional[str] = Field(None, description="MHCLO fragment of current asset")
    proposed_asset_id: Optional[str] = Field(None, description="Proposed asset ID (e.g. 'afro01', 'bald', 'eyebrow006')")
    proposed_display_name: Optional[str] = Field(None, description="Human-readable proposed asset name")
    proposed_fragment: Optional[str] = Field(None, description="MHCLO fragment of proposed asset (None for bald)")


class RefinementResponse(BaseModel):
    status: str = Field(..., description="Status: 'PREVIEW_READY' or 'REJECTED'")
    mode: str = Field("dry_run", description="Execution mode: strictly 'dry_run' (offline simulation)")
    case_id: Optional[str] = None
    input_text: str
    feature_id: Optional[str] = None
    display_name: Optional[str] = None

    # State audit fields
    reference_value: Optional[float] = Field(None, description="Offline cached reference value from verified baseline; NOT a live Blender read")
    current_value: Optional[float] = Field(None, description="Alias for reference_value for backward compatibility")
    value_source: str = Field("cached_reference", description="Source of truth for reference value: 'cached_reference'")
    is_live_blender_value: bool = Field(False, description="Explicitly False: this is an offline dry-run calculation")
    reference_note: str = Field(
        "Value is an offline cached reference value from the verified baseline; this is NOT a live Blender socket read.",
        description="Disclaimer note on data source"
    )

    # Bilateral side values when applicable
    left_current_value: Optional[float] = Field(None, description="Observed left value for bilateral features")
    right_current_value: Optional[float] = Field(None, description="Observed right value for bilateral features")
    left_proposed_value: Optional[float] = Field(None, description="Proposed left value for bilateral features")
    right_proposed_value: Optional[float] = Field(None, description="Proposed right value for bilateral features")
    is_symmetric: Optional[bool] = Field(None, description="Whether current bilateral values are symmetric")

    # Adjustment details
    adjustment_delta: Optional[float] = Field(None, description="Signed adjustment amount (e.g. +0.05)")
    proposed_delta: Optional[float] = Field(None, description="Alias for adjustment_delta")
    proposed_value: Optional[float] = Field(None, description="Proposed new value after adjustment")
    is_boundary_clamped: bool = Field(False, description="Whether proposed value was clamped at [-1.0, 1.0]")
    boundary_warning: Optional[str] = Field(None, description="Warning message if value was clamped to boundary")

    # Target identifiers
    target_identifier: Optional[str] = Field(None, description="Primary target identifier")
    target_identifiers: List[str] = Field(default_factory=list, description="All target identifiers touched (both sides for bilateral)")
    target_shapekeys: List[str] = Field(default_factory=list, description="Specific Blender shape keys that would be modified")

    # Parser audit fields
    parser_mode: Optional[str] = Field("rule_based", description="Parser mode used: 'rule_based' or 'ai'")
    parser_model: Optional[str] = Field(None, description="Model used if AI parser was selected (e.g. 'qwen3:4b')")

    proposed_payload: Optional[ProposedPayload] = None
    features: Optional[List[FeatureAdjustmentPreview]] = Field(None, description="Detailed list of all feature adjustments in the batch")
    asset_adjustments: Optional[List[AssetAdjustmentPreview]] = Field(None, description="Detailed list of asset adjustments (hair/eyebrows)")
    message: str
    error_message: Optional[str] = None
    log_id: Optional[int] = None

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    allowlist_count: int
    allowlist_features: List[str]
    mode: str
    database_connected: bool
    data_source_mode: str = Field("offline_cached_reference", description="Backend operates offline with verified cached reference values")
    parser_mode: str = Field("rule_based", description="Configured default parser mode ('rule_based' or 'ai')")
    ollama_model: Optional[str] = Field(None, description="Configured Ollama model name")
    ollama_available: Optional[bool] = Field(None, description="Whether the local Ollama instance is currently reachable")

class FeatureInfo(BaseModel):
    feature_id: str
    display_name: str
    section: str
    category: str
    is_sided: bool
    sides: List[str]
    adjustment_step: float
    min_value: float
    max_value: float
    reference_value: float
    baseline_value: float
    value_source: str = "cached_reference"
    target_identifiers: List[str]
    positive_targets: List[str]
    negative_targets: List[str]
    description: str
    example_increase: str
    example_decrease: str

class LiveFeatureState(BaseModel):
    feature_id: str
    display_name: str
    section: str
    category: str
    is_sided: bool
    side: str
    value: float = Field(..., description="Current live value read from Blender")
    left_value: Optional[float] = Field(None, description="Left side value for bilateral features")
    right_value: Optional[float] = Field(None, description="Right side value for bilateral features")
    is_symmetric: Optional[bool] = Field(None, description="Whether left and right values match for bilateral features")
    target_identifiers: List[str] = Field(default_factory=list)

class EquippedAssetInfo(BaseModel):
    name: str = Field(..., description="Object name in Blender (e.g. 'Human.short01')")
    object_type: str = Field(..., description="Asset type: 'Hair', 'Eyebrows', 'Eyes', etc.")
    asset_source: Optional[str] = Field(None, description="MHCLO fragment or source path")
    asset_id: Optional[str] = Field(None, description="Resolved catalog asset ID if recognized")
    in_current_scene: bool = Field(True, description="Whether currently present in active scene")

class LiveStateResponse(BaseModel):
    blender_available: bool = Field(..., description="Whether the connection to the MPFB Bridge in Blender succeeded")
    character_name: str = Field(..., description="Name of the character inspected in Blender")
    source: str = Field(..., description="'live_blender' if successfully read, 'unavailable' otherwise")
    timestamp_utc: str = Field(..., description="UTC timestamp of the read attempt")
    features: Optional[Dict[str, LiveFeatureState]] = Field(None, description="Current live values for allowlisted features")
    equipped_hair: Optional[EquippedAssetInfo] = Field(None, description="Currently equipped hair asset")
    equipped_eyebrows: Optional[EquippedAssetInfo] = Field(None, description="Currently equipped eyebrow asset")
    equipped_assets: Optional[List[EquippedAssetInfo]] = Field(None, description="All equipped assets on character")
    raw_modifier_count: Optional[int] = Field(None, description="Total active modifiers reported on the character")
    macro_count: Optional[int] = Field(None, description="Count of macro shape keys on basemesh")
    asymmetries: Optional[List[Dict[str, Any]]] = Field(None, description="Any detected bilateral asymmetries on the character")
    error_details: Optional[str] = Field(None, description="Diagnostic error explanation if connection or read failed")

class RefinementApplyRequest(BaseModel):
    preview_log_id: int = Field(..., description="ID of the previously recorded PREVIEW_READY refinement in SQLite audit log")
    case_id: Optional[str] = Field(None, description="Optional case identifier for tracking")
    character_name: str = Field("Human", description="Character object in Blender. Must be strictly 'Human'.")
    confirm_apply: bool = Field(..., description="Explicit confirmation requirement to apply modifications to Blender")

class RefinementApplyResponse(BaseModel):
    status: str = Field(..., description="'APPLIED' or 'APPLY_FAILED'")
    apply_log_id: Optional[int] = Field(None, description="ID of the audit record for this live_apply operation")
    preview_log_id: int = Field(..., description="ID of the preview log entry being applied")
    case_id: Optional[str] = Field(None, description="Case identifier")
    character_name: str = Field("Human", description="Target character object in Blender")
    feature_id: Optional[str] = Field(None, description="Allowlisted feature ID modified")
    display_name: Optional[str] = Field(None, description="Human-readable feature name")
    previous_value: Optional[float] = Field(None, description="Value prior to modification (unsided)")
    applied_value: Optional[float] = Field(None, description="Live value after modification read back from Blender (unsided)")
    left_previous_value: Optional[float] = Field(None, description="Left value prior to modification (bilateral)")
    right_previous_value: Optional[float] = Field(None, description="Right value prior to modification (bilateral)")
    left_applied_value: Optional[float] = Field(None, description="Left live value read back from Blender (bilateral)")
    right_applied_value: Optional[float] = Field(None, description="Right live value read back from Blender (bilateral)")
    verified: bool = Field(False, description="Whether immediate post-read verification confirmed target value within 0.001")
    drift_checked: bool = Field(False, description="Whether pre-mutation live drift check succeeded against baseline")
    modifiers_applied: Optional[List[Dict[str, Any]]] = Field(None, description="Exact modifiers applied to Blender")
    features_applied: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed breakdown of all features applied in batch")
    assets_applied: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed breakdown of all asset swaps applied")
    message: str = Field(..., description="Outcome summary message")
    error_message: Optional[str] = Field(None, description="Diagnostic error details if rejected or verification failed")

class SketchRenderRequest(BaseModel):
    case_id: Optional[str] = Field(None, description="Optional case identifier for investigation tracking")
    character_name: str = Field("Human", description="Name of the character in Blender. Must be strictly 'Human'.")

class SketchRenderResponse(BaseModel):
    status: str = Field(..., description="'SUCCESS' or 'FAILED'")
    character_name: str = Field("Human", description="Target character object in Blender")
    case_id: Optional[str] = Field(None, description="Case identifier if provided")
    image_url: Optional[str] = Field(None, description="Relative URL to retrieve sketch image (e.g. /sketches/<file>)")
    filename: Optional[str] = Field(None, description="Output filename")
    filepath: Optional[str] = Field(None, description="Full filesystem path of the saved sketch")
    filesize_bytes: Optional[int] = Field(None, description="Size of generated image in bytes")
    dimensions: Optional[List[int]] = Field(default_factory=lambda: [1024, 1024], description="Image dimensions [width, height]")
    timestamp_utc: str = Field(..., description="UTC ISO timestamp of sketch generation")
    message: str = Field(..., description="Summary outcome message")
    error_message: Optional[str] = Field(None, description="Diagnostic error details if failed")

