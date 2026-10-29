import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PreviewPanel } from '../components/PreviewPanel'
import type { RefinementResponse, RefinementApplyResponse } from '../types/api'

describe('PreviewPanel Component', () => {
  it('renders empty state when no refinement has been run', () => {
    render(<PreviewPanel preview={null} isLoading={false} networkError={null} />)
    expect(screen.getByText('No Active Refinement')).toBeInTheDocument()
    expect(screen.getByText('Generate & Apply')).toBeInTheDocument()
  })

  it('renders loading state when simulation or apply is in flight', () => {
    render(
      <PreviewPanel
        preview={null}
        isLoading={true}
        loadingStage="applying"
        networkError={null}
      />
    )
    expect(screen.getByText(/Applying Changes to Blender.../i)).toBeInTheDocument()
  })

  it('renders network error state when backend is unreachable', () => {
    render(
      <PreviewPanel
        preview={null}
        isLoading={false}
        networkError="Network connection failed when reaching backend at http://127.0.0.1:8000."
      />
    )
    expect(screen.getByText(/Backend Server Unreachable/i)).toBeInTheDocument()
    expect(screen.getByText(/Network connection failed/i)).toBeInTheDocument()
  })

  it('renders rejected refinement clearly without calling apply', () => {
    const mockRejectedPreview: RefinementResponse = {
      status: 'REJECTED',
      mode: 'dry_run',
      case_id: 'CASE-REJ-001',
      input_text: 'Make suspect hair blonde and long.',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Rejected',
      is_boundary_clamped: false,
      target_identifiers: [],
      target_shapekeys: [],
      message: 'Refinement rejected: Feature hair is not supported in allowlist.',
      error_message: 'Feature hair is not supported in allowlist.',
    }

    render(
      <PreviewPanel
        preview={mockRejectedPreview}
        applyResult={null}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('REJECTED')).toBeInTheDocument()
    expect(screen.getByText('Blender Unmodified')).toBeInTheDocument()
    expect(screen.getByText(/Feature hair is not supported in allowlist/i)).toBeInTheDocument()
    expect(screen.getByText(/No modifications were sent to Blender/i)).toBeInTheDocument()
  })

  it('renders successful apply result with read-back verification and update confirmation', () => {
    const mockPreview: RefinementResponse = {
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-001',
      input_text: 'Make the nose slightly wider.',
      feature_id: 'nose_width',
      display_name: 'nose width',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      proposed_delta: 0.05,
      proposed_value: 0.25,
      is_boundary_clamped: false,
      target_identifiers: ['nose:nose-scale-horiz-decr-incr:unsided'],
      target_shapekeys: ['nose-scale-horiz-incr'],
      message: 'Preview ready',
      log_id: 1,
    }

    const mockApplyResult: RefinementApplyResponse = {
      status: 'APPLIED',
      apply_log_id: 2,
      preview_log_id: 1,
      case_id: 'CASE-001',
      character_name: 'Human',
      feature_id: 'nose_width',
      display_name: 'nose width',
      previous_value: 0.2,
      applied_value: 0.25,
      left_previous_value: null,
      right_previous_value: null,
      left_applied_value: null,
      right_applied_value: null,
      verified: true,
      drift_checked: true,
      modifiers_applied: [
        {
          section: 'nose',
          category: 'nose-scale-horiz-decr-incr',
          side: 'unsided',
          value: 0.25,
        },
      ],
      message: 'Successfully applied and verified changes to nose width on character Human in Blender.',
      error_message: null,
    }

    render(
      <PreviewPanel
        preview={mockPreview}
        applyResult={mockApplyResult}
        isLoading={false}
        networkError={null}
      />
    )

    // Outcome banner
    expect(screen.getByText('BLENDER UPDATED')).toBeInTheDocument()
    expect(screen.getByText('Verified Read-Back')).toBeInTheDocument()

    // Key metrics grid
    expect(screen.getByText('AI Interpretation')).toBeInTheDocument()
    expect(screen.getByText('Blender Updated?')).toBeInTheDocument()
    expect(screen.getByText('YES — Applied')).toBeInTheDocument()
    expect(screen.getByText('Read-Back Verification')).toBeInTheDocument()
    expect(screen.getByText('PASSED (±0.001)')).toBeInTheDocument()

    // Value progression
    expect(screen.getByText('+0.20')).toBeInTheDocument()
    expect(screen.getByText('+0.25')).toBeInTheDocument()
  })

  it('renders apply failure with failure details and state drift explanation', () => {
    const mockPreview: RefinementResponse = {
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-001',
      input_text: 'Make the nose slightly wider.',
      feature_id: 'nose_width',
      display_name: 'nose width',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      proposed_delta: 0.05,
      proposed_value: 0.25,
      is_boundary_clamped: false,
      target_identifiers: ['nose:nose-scale-horiz-decr-incr:unsided'],
      target_shapekeys: ['nose-scale-horiz-incr'],
      message: 'Preview ready',
      log_id: 1,
    }

    const mockFailedApply: RefinementApplyResponse = {
      status: 'APPLY_FAILED',
      apply_log_id: 3,
      preview_log_id: 1,
      case_id: 'CASE-001',
      character_name: 'Human',
      feature_id: 'nose_width',
      display_name: 'nose width',
      verified: false,
      drift_checked: true,
      message: 'Application rejected: State drift detected for feature nose width.',
      error_message:
        'State drift detected for feature nose width. Baseline captured during preview was +0.20, but live Blender model is currently at +0.35.',
    }

    render(
      <PreviewPanel
        preview={mockPreview}
        applyResult={mockFailedApply}
        isLoading={false}
        networkError={null}
      />
    )

    // Failure banner
    expect(screen.getByText('APPLY FAILED')).toBeInTheDocument()
    expect(screen.getByText('Verification Incomplete')).toBeInTheDocument()
    expect(screen.getByText('NO — Aborted')).toBeInTheDocument()
    expect(screen.getByText('FAILED')).toBeInTheDocument()

    // Diagnostic details
    expect(screen.getByText(/State drift detected for feature nose width/i)).toBeInTheDocument()
    expect(screen.getByText(/submit a fresh adjustment against the current live Blender state/i)).toBeInTheDocument()
  })

  it('renders multi-feature dry-run preview breakdown table with all proposed adjustments', () => {
    const mockMultiPreview: RefinementResponse = {
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-MULTI-PREV',
      input_text: 'A person with a broad nose and small eyes.',
      feature_id: 'multi_feature',
      display_name: 'Multi-Feature Batch (2 features)',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      proposed_delta: 0.0,
      is_boundary_clamped: false,
      target_identifiers: [
        'nose:nose-scale-horiz-decr-incr:unsided',
        'eyes:eye-scale-decr-incr:left',
        'eyes:eye-scale-decr-incr:right'
      ],
      target_shapekeys: ['nose-scale-horiz-incr', 'l-eye-scale-decr', 'r-eye-scale-decr'],
      features: [
        {
          feature_id: 'nose_width',
          display_name: 'nose width',
          section: 'nose',
          category: 'nose-scale-horiz-decr-incr',
          is_sided: false,
          side: 'unsided',
          direction: 1,
          magnitude: 'slight',
          adjustment_delta: 0.05,
          current_value: 0.20,
          proposed_value: 0.25,
          is_boundary_clamped: false,
          target_identifiers: ['nose:nose-scale-horiz-decr-incr:unsided'],
          target_shapekeys: ['nose-scale-horiz-incr']
        },
        {
          feature_id: 'eye_size',
          display_name: 'eye size',
          section: 'eyes',
          category: 'eye-scale-decr-incr',
          is_sided: true,
          side: 'left,right',
          direction: -1,
          magnitude: 'slight',
          adjustment_delta: -0.05,
          left_current_value: 0.10,
          right_current_value: 0.10,
          left_proposed_value: 0.05,
          right_proposed_value: 0.05,
          is_boundary_clamped: false,
          target_identifiers: ['eyes:eye-scale-decr-incr:left', 'eyes:eye-scale-decr-incr:right'],
          target_shapekeys: ['l-eye-scale-decr', 'r-eye-scale-decr']
        }
      ],
      message: 'Live dry-run preview: 2 facial adjustments proposed [nose width, eye size] across 3 morph targets.',
      log_id: 10
    }

    render(
      <PreviewPanel
        preview={mockMultiPreview}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('PREVIEW READY')).toBeInTheDocument()
    expect(screen.getByText('Multi-Feature Batch (2 features)')).toBeInTheDocument()
    expect(screen.getByText('nose width')).toBeInTheDocument()
    expect(screen.getByText('eye size')).toBeInTheDocument()
    expect(screen.getByText('+0.05')).toBeInTheDocument()
    expect(screen.getByText('-0.05')).toBeInTheDocument()
  })

  it('renders multi-feature applied result breakdown table with verified badges', () => {
    const mockMultiApply: RefinementApplyResponse = {
      status: 'APPLIED',
      apply_log_id: 11,
      preview_log_id: 10,
      case_id: 'CASE-MULTI-APPLY',
      character_name: 'Human',
      feature_id: 'multi_feature',
      display_name: 'Multi-Feature Batch (2 features)',
      verified: true,
      drift_checked: true,
      features_applied: [
        {
          feature_id: 'nose_width',
          display_name: 'nose width',
          is_sided: false,
          previous_value: 0.20,
          applied_value: 0.25,
          verified: true
        },
        {
          feature_id: 'eye_size',
          display_name: 'eye size',
          is_sided: true,
          previous_left_value: 0.10,
          previous_right_value: 0.10,
          applied_left_value: 0.05,
          applied_right_value: 0.05,
          verified: true
        }
      ],
      message: 'Successfully applied and verified 2 facial adjustments on character Human in Blender.',
      error_message: null
    }

    render(
      <PreviewPanel
        preview={null}
        applyResult={mockMultiApply}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('BLENDER UPDATED')).toBeInTheDocument()
    expect(screen.getByText('Verified Read-Back')).toBeInTheDocument()
    expect(screen.getByText('Successfully Applied: Multi-Feature Batch (2 features)')).toBeInTheDocument()
    expect(screen.getByText('nose width')).toBeInTheDocument()
    expect(screen.getByText('eye size')).toBeInTheDocument()
    expect(screen.getAllByText('✓ Verified')).toHaveLength(2)
  })

  it('renders proposed asset customization preview cards for hair and eyebrows', () => {
    const mockAssetPreview: RefinementResponse = {
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-ASSET-01',
      input_text: 'Change hairstyle to a bob cut and curved eyebrows.',
      feature_id: 'asset_customization',
      display_name: 'Hair / Eyebrow Customization',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      is_boundary_clamped: false,
      target_identifiers: [],
      target_shapekeys: [],
      asset_adjustments: [
        {
          asset_type: 'hair',
          action: 'swap',
          current_asset_id: 'short01',
          current_asset_name: 'Human.short01',
          current_fragment: 'short01/short01.mhclo',
          proposed_asset_id: 'bob01',
          proposed_display_name: 'Bob Cut',
          proposed_fragment: 'bob01/bob01.mhclo'
        },
        {
          asset_type: 'eyebrows',
          action: 'swap',
          current_asset_id: 'eyebrow003',
          current_asset_name: 'Human.eyebrow003',
          current_fragment: 'eyebrow003/eyebrow003.mhclo',
          proposed_asset_id: 'eyebrow009',
          proposed_display_name: 'Curved Eyebrows',
          proposed_fragment: 'eyebrow009/eyebrow009.mhclo'
        }
      ],
      message: 'Preview ready. Asset changes: [Hair: short01 -> Bob Cut, Eyebrows: eyebrow003 -> Curved Eyebrows].',
      log_id: 15
    }

    render(
      <PreviewPanel
        preview={mockAssetPreview}
        applyResult={null}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('PREVIEW READY')).toBeInTheDocument()
    expect(screen.getByText('Proposed Asset Customizations')).toBeInTheDocument()
    expect(screen.getByText('Bob Cut')).toBeInTheDocument()
    expect(screen.getByText('Curved Eyebrows')).toBeInTheDocument()
    expect(screen.getByText(/Current: Human.short01/i)).toBeInTheDocument()
  })

  it('renders applied asset modifications with object names and verification badges', () => {
    const mockAssetApply: RefinementApplyResponse = {
      status: 'APPLIED',
      apply_log_id: 16,
      preview_log_id: 15,
      case_id: 'CASE-ASSET-01',
      character_name: 'Human',
      feature_id: 'asset_customization',
      display_name: 'Hair / Eyebrow Customization',
      verified: true,
      drift_checked: true,
      assets_applied: [
        {
          asset_type: 'hair',
          action: 'swap',
          applied_asset_name: 'Human.bob01',
          asset_id: 'bob01',
          display_name: 'Bob Cut',
          fragment: 'bob01/bob01.mhclo',
          verified: true
        },
        {
          asset_type: 'eyebrows',
          action: 'swap',
          applied_asset_name: 'Human.eyebrow009',
          asset_id: 'eyebrow009',
          display_name: 'Curved Eyebrows',
          fragment: 'eyebrow009/eyebrow009.mhclo',
          verified: true
        }
      ],
      message: 'Successfully applied and verified 2 asset changes on character Human in Blender.',
      error_message: null
    }

    render(
      <PreviewPanel
        preview={null}
        applyResult={mockAssetApply}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('BLENDER UPDATED')).toBeInTheDocument()
    expect(screen.getByText('Verified Read-Back')).toBeInTheDocument()
    expect(screen.getByText('Equipped Assets Modified')).toBeInTheDocument()
    expect(screen.getByText('Bob Cut')).toBeInTheDocument()
    expect(screen.getByText('Curved Eyebrows')).toBeInTheDocument()
    expect(screen.getByText('Human.bob01')).toBeInTheDocument()
    expect(screen.getByText('Human.eyebrow009')).toBeInTheDocument()
  })

  it('renders forensic sketch portrait when sketchResult is provided', () => {
    const mockSketch = {
      status: 'SUCCESS' as const,
      character_name: 'Human',
      case_id: 'CASE-PANEL-01',
      image_url: '/sketches/sketch_20261029_panel.png',
      filename: 'sketch_20261029_panel.png',
      filepath: 'C:/Dept/CrimeSketchAI/sketches/sketch_20261029_panel.png',
      filesize_bytes: 350000,
      dimensions: [1024, 1024] as [number, number],
      timestamp_utc: '2026-10-29T03:30:00Z',
      message: "Forensic pencil sketch successfully generated for 'Human'.",
      error_message: null,
    }

    render(
      <PreviewPanel
        preview={null}
        applyResult={null}
        sketchResult={mockSketch}
        isLoading={false}
        networkError={null}
      />
    )

    expect(screen.getByText('FORENSIC SKETCH')).toBeInTheDocument()
    expect(screen.getByText('1024 × 1024 PNG')).toBeInTheDocument()
    expect(screen.getByText('CASE-PANEL-01')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Forensic Sketch - Human/i })).toBeInTheDocument()
  })
})
