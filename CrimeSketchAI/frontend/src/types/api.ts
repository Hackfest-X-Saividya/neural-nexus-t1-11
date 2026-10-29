/**
 * TypeScript API interfaces for CrimeSketchAI.
 * Exactly matches FastAPI backend Pydantic schemas.
 */

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  app_name: string;
  version: string;
  allowlist_count: number;
  allowlist_features: string[];
  mode: string;
  database_connected: boolean;
  data_source_mode: string;
  parser_mode?: string;
  ollama_model?: string | null;
  ollama_available?: boolean | null;
}

export interface FeatureInfo {
  feature_id: string;
  display_name: string;
  section: string;
  category: string;
  is_sided: boolean;
  sides: string[];
  adjustment_step: floatNumber;
  min_value: floatNumber;
  max_value: floatNumber;
  reference_value: floatNumber;
  baseline_value: floatNumber;
  value_source: string;
  target_identifiers: string[];
  positive_targets: string[];
  negative_targets: string[];
  description: string;
  example_increase: string;
  example_decrease: string;
}

type floatNumber = number;

export interface LiveFeatureState {
  feature_id: string;
  display_name: string;
  section: string;
  category: string;
  is_sided: boolean;
  side: string;
  value: number;
  left_value?: number | null;
  right_value?: number | null;
  is_symmetric?: boolean | null;
  target_identifiers: string[];
}

export interface EquippedAssetInfo {
  name: string;
  object_type: string;
  asset_source?: string | null;
  asset_id?: string | null;
  in_current_scene?: boolean;
}

export interface AssetAdjustmentPreview {
  asset_type: 'hair' | 'eyebrows';
  action: 'swap' | 'remove' | 'add';
  current_asset_id?: string | null;
  current_asset_name?: string | null;
  current_fragment?: string | null;
  proposed_asset_id?: string | null;
  proposed_display_name?: string | null;
  proposed_fragment?: string | null;
}

export interface LiveStateResponse {
  blender_available: boolean;
  character_name: string;
  source: 'live_blender' | 'unavailable';
  timestamp_utc: string;
  features?: Record<string, LiveFeatureState> | null;
  equipped_hair?: EquippedAssetInfo | null;
  equipped_eyebrows?: EquippedAssetInfo | null;
  equipped_assets?: EquippedAssetInfo[] | null;
  raw_modifier_count?: number | null;
  macro_count?: number | null;
  asymmetries?: Array<Record<string, unknown>> | null;
  error_details?: string | null;
}

export interface ProposedModifier {
  section: string;
  category: string;
  side: string;
  value: number;
}

export interface ProposedPayload {
  name: string;
  modifiers: ProposedModifier[];
  symmetry: boolean;
  prune: boolean;
  refit: boolean;
}

export interface RefinementRequest {
  text: string;
  case_id?: string | null;
  character_name?: string | null;
  use_live_state?: boolean;
  parser_mode?: 'rule_based' | 'ai' | null;
  // current_value is strictly forbidden on backend; omitted from client
}

export interface FeatureAdjustmentPreview {
  feature_id: string;
  display_name: string;
  section: string;
  category: string;
  is_sided: boolean;
  side: string;
  direction: number;
  magnitude: string;
  adjustment_delta: number;
  current_value?: number | null;
  proposed_value?: number | null;
  left_current_value?: number | null;
  right_current_value?: number | null;
  left_proposed_value?: number | null;
  right_proposed_value?: number | null;
  is_symmetric?: boolean | null;
  is_boundary_clamped: boolean;
  boundary_warning?: string | null;
  target_identifiers: string[];
  target_shapekeys: string[];
}

export interface RefinementResponse {
  status: 'PREVIEW_READY' | 'REJECTED';
  mode: string;
  case_id?: string | null;
  input_text: string;
  feature_id?: string | null;
  display_name?: string | null;
  parser_mode?: string | null;
  parser_model?: string | null;

  // State audit fields
  reference_value?: number | null;
  current_value?: number | null;
  value_source: 'cached_reference' | 'live_blender' | 'unavailable' | string;
  is_live_blender_value: boolean;
  reference_note: string;

  // Bilateral side values
  left_current_value?: number | null;
  right_current_value?: number | null;
  left_proposed_value?: number | null;
  right_proposed_value?: number | null;
  is_symmetric?: boolean | null;

  // Adjustment details
  adjustment_delta?: number | null;
  proposed_delta?: number | null;
  proposed_value?: number | null;
  is_boundary_clamped: boolean;
  boundary_warning?: string | null;

  // Target identifiers
  target_identifier?: string | null;
  target_identifiers: string[];
  target_shapekeys: string[];

  proposed_payload?: ProposedPayload | null;
  features?: FeatureAdjustmentPreview[] | null;
  asset_adjustments?: AssetAdjustmentPreview[] | null;
  message: string;
  error_message?: string | null;
  log_id?: number | null;
}

export interface AuditLogEntry {
  id: number;
  timestamp_utc: string;
  request_text: string;
  case_id?: string | null;
  mode: string;
  status: string;
  parsed_feature?: string | null;
  target_identifier?: string | null;
  current_value?: number | null;
  proposed_delta?: number | null;
  proposed_value?: number | null;
  error_message?: string | null;
  details_json?: string | null;
}

export interface RefinementApplyRequest {
  preview_log_id: number;
  case_id?: string | null;
  character_name?: string;
  confirm_apply: boolean;
}

export interface RefinementApplyResponse {
  status: 'APPLIED' | 'APPLY_FAILED';
  apply_log_id?: number | null;
  preview_log_id: number;
  case_id?: string | null;
  character_name: string;
  feature_id?: string | null;
  display_name?: string | null;
  previous_value?: number | null;
  applied_value?: number | null;
  left_previous_value?: number | null;
  right_previous_value?: number | null;
  left_applied_value?: number | null;
  right_applied_value?: number | null;
  verified: boolean;
  drift_checked: boolean;
  modifiers_applied?: Array<{
    section: string;
    category: string;
    side: string;
    value: number;
  }> | null;
  features_applied?: Array<Record<string, unknown>> | null;
  assets_applied?: Array<{
    asset_type: string;
    action: string;
    applied_asset_name?: string | null;
    removed_asset_name?: string | null;
    asset_id?: string | null;
    fragment?: string | null;
    display_name?: string | null;
    verified: boolean;
  }> | null;
  message: string;
  error_message?: string | null;
}

export interface SketchRenderRequest {
  case_id?: string | null;
  character_name?: string;
}

export interface SketchRenderResponse {
  status: 'SUCCESS' | 'FAILED';
  character_name: string;
  case_id?: string | null;
  image_url?: string | null;
  filename?: string | null;
  filepath?: string | null;
  filesize_bytes?: number | null;
  dimensions?: [number, number] | null;
  timestamp_utc: string;
  message: string;
  error_message?: string | null;
}



