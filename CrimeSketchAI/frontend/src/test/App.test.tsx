import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { App } from '../App'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getHealth: vi.fn(),
    getLiveState: vi.fn(),
    getFeatures: vi.fn(),
    postRefine: vi.fn(),
    postApply: vi.fn(),
    getLogs: vi.fn(),
  },
}))

describe('App Integration Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'healthy',
      app_name: 'CrimeSketchAI Refinement Backend',
      version: '0.1.0',
      allowlist_count: 10,
      allowlist_features: ['nose_width'],
      mode: 'live_apply',
      database_connected: true,
      data_source_mode: 'live_blender',
      ollama_available: true,
      ollama_model: 'qwen3:4b',
    })

    vi.mocked(api.getLiveState).mockResolvedValue({
      blender_available: true,
      character_name: 'Human',
      source: 'live_blender',
      timestamp_utc: '2026-10-28T12:00:00Z',
      features: {},
    })

    vi.mocked(api.getLogs).mockResolvedValue([])
  })

  it('renders header, workspace, and loads initial status', async () => {
    render(<App />)

    expect(screen.getByText('CrimeSketchAI')).toBeInTheDocument()
    expect(screen.getByText(/Refinement Workspace/i)).toBeInTheDocument()
    expect(screen.getByText(/Forensic Audit Trail/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(api.getHealth).toHaveBeenCalledTimes(1)
      expect(api.getLiveState).toHaveBeenCalledWith('Human')
      expect(api.getLogs).toHaveBeenCalled()
    })

    expect(await screen.findByText('Connected (Human)')).toBeInTheDocument()
  })

  it('executes successful 1-click refine -> apply workflow and updates UI', async () => {
    vi.mocked(api.postRefine).mockResolvedValue({
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-2026-001',
      input_text: 'Make the nose slightly wider.',
      feature_id: 'nose_width',
      display_name: 'nose width',
      reference_value: 0.2,
      current_value: 0.2,
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      proposed_delta: 0.05,
      proposed_value: 0.25,
      is_boundary_clamped: false,
      target_identifiers: ['nose:nose-scale-horiz-decr-incr:unsided'],
      target_shapekeys: ['nose-scale-horiz-incr'],
      message: 'Preview ready',
      log_id: 101,
    })

    vi.mocked(api.postApply).mockResolvedValue({
      status: 'APPLIED',
      apply_log_id: 202,
      preview_log_id: 101,
      case_id: 'CASE-2026-001',
      character_name: 'Human',
      feature_id: 'nose_width',
      display_name: 'nose width',
      previous_value: 0.2,
      applied_value: 0.25,
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
    })

    render(<App />)

    // Click primary "Generate & Apply" button
    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    fireEvent.click(submitBtn)

    // Verify refine called with live Blender state and Ollama AI parser
    await waitFor(() => {
      expect(api.postRefine).toHaveBeenCalledWith({
        text: 'Make the nose slightly wider.',
        case_id: 'CASE-2026-001',
        character_name: 'Human',
        use_live_state: true,
        parser_mode: 'ai',
      })
    })

    // Verify apply was called with preview_log_id: 101 and confirm_apply: true
    await waitFor(() => {
      expect(api.postApply).toHaveBeenCalledWith({
        preview_log_id: 101,
        case_id: 'CASE-2026-001',
        character_name: 'Human',
        confirm_apply: true,
      })
    })

    // Verify UI displays success confirmation
    expect(await screen.findByText('BLENDER UPDATED')).toBeInTheDocument()
    expect(screen.getByText('Verified Read-Back')).toBeInTheDocument()
    expect(screen.getByText('YES — Applied')).toBeInTheDocument()
    expect(screen.getByText('PASSED (±0.001)')).toBeInTheDocument()
  })

  it('stops and does NOT call apply when refinement is rejected', async () => {
    vi.mocked(api.postRefine).mockResolvedValue({
      status: 'REJECTED',
      mode: 'dry_run',
      case_id: 'CASE-2026-001',
      input_text: 'Give suspect blue eyes.',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Rejected',
      is_boundary_clamped: false,
      target_identifiers: [],
      target_shapekeys: [],
      message: 'Refinement rejected: Eye color is not in allowlist.',
      error_message: 'Eye color is not in allowlist.',
    })

    render(<App />)

    const textarea = screen.getByLabelText(/Natural-Language Refinement Command/i)
    fireEvent.change(textarea, { target: { value: 'Give suspect blue eyes.' } })

    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(api.postRefine).toHaveBeenCalledTimes(1)
    })

    // Assert apply was NEVER called
    expect(api.postApply).not.toHaveBeenCalled()

    // Assert UI shows rejection
    expect(await screen.findByText('REJECTED')).toBeInTheDocument()
    expect(screen.getByText('Blender Unmodified')).toBeInTheDocument()
    expect(screen.getByText(/Eye color is not in allowlist/i)).toBeInTheDocument()
  })

  it('displays failure details when apply returns status APPLY_FAILED', async () => {
    vi.mocked(api.postRefine).mockResolvedValue({
      status: 'PREVIEW_READY',
      mode: 'dry_run',
      case_id: 'CASE-2026-001',
      input_text: 'Make the nose slightly wider.',
      feature_id: 'nose_width',
      display_name: 'nose width',
      reference_value: 0.2,
      current_value: 0.2,
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'Live Blender',
      proposed_delta: 0.05,
      proposed_value: 0.25,
      is_boundary_clamped: false,
      target_identifiers: ['nose:nose-scale-horiz-decr-incr:unsided'],
      target_shapekeys: ['nose-scale-horiz-incr'],
      message: 'Preview ready',
      log_id: 103,
    })

    vi.mocked(api.postApply).mockResolvedValue({
      status: 'APPLY_FAILED',
      apply_log_id: 204,
      preview_log_id: 103,
      case_id: 'CASE-2026-001',
      character_name: 'Human',
      feature_id: 'nose_width',
      display_name: 'nose width',
      verified: false,
      drift_checked: true,
      message: 'Application rejected: State drift detected for feature nose width.',
      error_message:
        'State drift detected for feature nose width. Baseline captured during preview was +0.20, but live Blender model is currently at +0.35.',
    })

    render(<App />)

    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(api.postRefine).toHaveBeenCalledTimes(1)
      expect(api.postApply).toHaveBeenCalledTimes(1)
    })

    // Assert UI displays failure details
    expect(await screen.findByText('APPLY FAILED')).toBeInTheDocument()
    expect(screen.getByText('NO — Aborted')).toBeInTheDocument()
    expect(screen.getByText(/State drift detected for feature nose width/i)).toBeInTheDocument()
    // Assert BLENDER UPDATED is NOT displayed
    expect(screen.queryByText('BLENDER UPDATED')).not.toBeInTheDocument()
  })

  it('prevents duplicate submissions while workflow is in flight', async () => {
    let resolveRefine: (val: any) => void
    const refinePromise = new Promise((resolve) => {
      resolveRefine = resolve
    })
    vi.mocked(api.postRefine).mockReturnValue(refinePromise as any)

    render(<App />)

    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    fireEvent.click(submitBtn)

    // Button should now be disabled and showing processing text
    expect(submitBtn).toBeDisabled()

    // Attempt second click while in flight
    fireEvent.click(submitBtn)

    // Resolve initial call
    resolveRefine!({
      status: 'REJECTED',
      mode: 'dry_run',
      input_text: 'test',
      value_source: 'live_blender',
      is_live_blender_value: true,
      reference_note: 'done',
      is_boundary_clamped: false,
      target_identifiers: [],
      target_shapekeys: [],
      message: 'Rejected',
    })

    await waitFor(() => {
      expect(api.postRefine).toHaveBeenCalledTimes(1)
    })
  })
})
