import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RefinementForm } from '../components/RefinementForm'

describe('RefinementForm Component', () => {
  it('renders initial form fields with defaults and Generate & Apply button', () => {
    const mockGenerateAndApply = vi.fn()
    render(
      <RefinementForm
        onGenerateAndApply={mockGenerateAndApply}
        isLoading={false}
        blenderState={{
          blender_available: true,
          character_name: 'Human',
          source: 'live_blender',
          timestamp_utc: '2026-10-28T12:00:00Z',
        }}
        health={{
          status: 'healthy',
          app_name: 'CrimeSketchAI',
          version: '0.1.0',
          allowlist_count: 10,
          allowlist_features: ['nose_width'],
          mode: 'live_apply',
          database_connected: true,
          data_source_mode: 'live_blender',
          ollama_available: true,
          ollama_model: 'qwen3:4b',
        }}
      />
    )

    // Character select
    expect(screen.getByLabelText(/Character Model/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue(/Human \(Active 3D Subject\)/i)).toBeInTheDocument()

    // Mode options
    expect(screen.getByText(/Cached Reference Baseline/i)).toBeInTheDocument()
    expect(screen.getByText(/Live Blender Target Stack/i)).toBeInTheDocument()

    // Primary action button labelled "Generate & Apply"
    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    expect(submitBtn).toBeInTheDocument()
  })

  it('populates text input when clicking an example chip', () => {
    const mockGenerateAndApply = vi.fn()
    render(
      <RefinementForm
        onGenerateAndApply={mockGenerateAndApply}
        isLoading={false}
        blenderState={null}
      />
    )

    const chip = screen.getByRole('button', {
      name: 'Make the cheekbones more prominent.',
    })
    fireEvent.click(chip)

    const textarea = screen.getByLabelText(
      /Natural-Language Refinement Command/i
    ) as HTMLTextAreaElement
    expect(textarea.value).toBe('Make the cheekbones more prominent.')
  })

  it('submits Generate & Apply with current inputs', () => {
    const mockGenerateAndApply = vi.fn()
    render(
      <RefinementForm
        onGenerateAndApply={mockGenerateAndApply}
        isLoading={false}
        blenderState={{
          blender_available: true,
          character_name: 'Human',
          source: 'live_blender',
          timestamp_utc: '2026-10-28T12:00:00Z',
        }}
      />
    )

    // Fill in command
    const textarea = screen.getByLabelText(/Natural-Language Refinement Command/i)
    fireEvent.change(textarea, { target: { value: 'Make the eyes smaller.' } })

    // Click submit
    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    fireEvent.click(submitBtn)

    expect(mockGenerateAndApply).toHaveBeenCalledTimes(1)
    expect(mockGenerateAndApply).toHaveBeenCalledWith({
      text: 'Make the eyes smaller.',
      caseId: 'CASE-2026-001',
      characterName: 'Human',
      parserMode: 'ai',
    })
  })

  it('disables submit button and controls when loading', () => {
    const mockGenerateAndApply = vi.fn()
    render(
      <RefinementForm
        onGenerateAndApply={mockGenerateAndApply}
        isLoading={true}
        loadingStage="applying"
        blenderState={null}
      />
    )

    expect(screen.getByText(/Applying to Blender.../i)).toBeInTheDocument()
    const submitBtn = screen.getByRole('button', {
      name: /Applying to Blender.../i,
    })
    expect(submitBtn).toBeDisabled()
  })

  it('prevents submission when input is empty', () => {
    const mockGenerateAndApply = vi.fn()
    render(
      <RefinementForm
        onGenerateAndApply={mockGenerateAndApply}
        isLoading={false}
        blenderState={null}
      />
    )

    const textarea = screen.getByLabelText(/Natural-Language Refinement Command/i)
    fireEvent.change(textarea, { target: { value: '   ' } })

    const submitBtn = screen.getByRole('button', {
      name: /Generate & Apply/i,
    })
    expect(submitBtn).toBeDisabled()
  })

  it('triggers onRenderSketch when Generate Sketch button is clicked', () => {
    const mockRenderSketch = vi.fn()
    render(
      <RefinementForm
        onRenderSketch={mockRenderSketch}
        isLoading={false}
        blenderState={null}
      />
    )

    const sketchBtn = screen.getByRole('button', { name: /Generate Sketch/i })
    expect(sketchBtn).toBeInTheDocument()

    fireEvent.click(sketchBtn)
    expect(mockRenderSketch).toHaveBeenCalledWith({
      caseId: 'CASE-2026-001',
      characterName: 'Human',
    })
  })
})
