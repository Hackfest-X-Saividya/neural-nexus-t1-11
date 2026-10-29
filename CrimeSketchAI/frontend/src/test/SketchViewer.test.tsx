import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SketchViewer } from '../components/SketchViewer'
import type { SketchRenderResponse } from '../types/api'

describe('SketchViewer Component', () => {
  it('renders empty state when no sketch has been rendered', () => {
    const mockRender = vi.fn()
    render(
      <SketchViewer
        sketchResult={null}
        isRenderingSketch={false}
        sketchError={null}
        onRenderSketch={mockRender}
      />
    )

    expect(screen.getByText('No Forensic Sketch Rendered')).toBeInTheDocument()
    const generateBtn = screen.getByRole('button', { name: /Generate Forensic Sketch/i })
    expect(generateBtn).toBeInTheDocument()

    fireEvent.click(generateBtn)
    expect(mockRender).toHaveBeenCalledTimes(1)
  })

  it('renders loading state when sketch rendering is in progress', () => {
    render(
      <SketchViewer
        sketchResult={null}
        isRenderingSketch={true}
        sketchError={null}
      />
    )

    expect(screen.getByText(/Rendering Forensic Pencil Sketch.../i)).toBeInTheDocument()
    expect(screen.getByText(/Exporting live character from Blender/i)).toBeInTheDocument()
  })

  it('renders error state when sketch generation fails', () => {
    const mockRetry = vi.fn()
    render(
      <SketchViewer
        sketchResult={null}
        isRenderingSketch={false}
        sketchError="Blender bridge socket closed unexpectedly at 127.0.0.1:9877."
        onRenderSketch={mockRetry}
      />
    )

    expect(screen.getByText('SKETCH FAILED')).toBeInTheDocument()
    expect(screen.getByText('Forensic Sketch Generation Failed')).toBeInTheDocument()
    expect(screen.getByText(/Blender bridge socket closed/i)).toBeInTheDocument()

    const retryBtn = screen.getByRole('button', { name: /Retry Render/i })
    fireEvent.click(retryBtn)
    expect(mockRetry).toHaveBeenCalledTimes(1)
  })

  it('renders successful forensic sketch portrait and metadata', () => {
    const mockSketch: SketchRenderResponse = {
      status: 'SUCCESS',
      character_name: 'Human',
      case_id: 'CASE-FORENSIC-88',
      image_url: '/sketches/sketch_20261029_CASE_88.png',
      filename: 'sketch_20261029_CASE_88.png',
      filepath: 'C:/Dept/CrimeSketchAI/sketches/sketch_20261029_CASE_88.png',
      filesize_bytes: 355305,
      dimensions: [1024, 1024],
      timestamp_utc: '2026-10-29T03:30:00Z',
      message: "Forensic pencil sketch successfully generated for 'Human'.",
      error_message: null,
    }

    render(
      <SketchViewer
        sketchResult={mockSketch}
        isRenderingSketch={false}
        sketchError={null}
      />
    )

    expect(screen.getByText('FORENSIC SKETCH')).toBeInTheDocument()
    expect(screen.getByText('1024 × 1024 PNG')).toBeInTheDocument()
    expect(screen.getByText('CASE-FORENSIC-88')).toBeInTheDocument()
    expect(screen.getByText('347.0 KB')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Forensic Sketch - Human/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Download/i })).toBeInTheDocument()
  })
})

