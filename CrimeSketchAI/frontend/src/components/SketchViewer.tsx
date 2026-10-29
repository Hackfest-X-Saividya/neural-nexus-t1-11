import React from 'react'
import type { SketchRenderResponse } from '../types/api'
import { API_BASE_URL } from '../api/client'

interface SketchViewerProps {
  sketchResult: SketchRenderResponse | null
  isRenderingSketch: boolean
  sketchError: string | null
  onRenderSketch?: () => void
  disabled?: boolean
}

export const SketchViewer: React.FC<SketchViewerProps> = ({
  sketchResult,
  isRenderingSketch,
  sketchError,
  onRenderSketch,
  disabled = false,
}) => {
  if (isRenderingSketch) {
    return (
      <div className="card sketch-viewer-card loading-state">
        <div className="spinner-lg" />
        <h3 className="loading-title">Rendering Forensic Pencil Sketch...</h3>
        <p className="loading-desc">
          Exporting live character from Blender, staging 85mm portrait camera, stripping helper geometry,
          and calculating monochrome graphite contour line art.
        </p>
      </div>
    )
  }

  if (sketchError) {
    return (
      <div className="card sketch-viewer-card sketch-error-card">
        <div className="preview-header-row">
          <div className="preview-title-group">
            <span className="badge badge-danger">SKETCH FAILED</span>
          </div>
          {onRenderSketch && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={onRenderSketch}
              disabled={disabled}
            >
              Retry Render
            </button>
          )}
        </div>
        <h4 className="error-title">Forensic Sketch Generation Failed</h4>
        <p className="error-body">{sketchError}</p>
      </div>
    )
  }

  if (!sketchResult || sketchResult.status !== 'SUCCESS') {
    return (
      <div className="card sketch-viewer-card sketch-empty-card">
        <div className="sketch-empty-icon">
          <svg
            viewBox="0 0 24 24"
            width="32"
            height="32"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </div>
        <h4 className="empty-title">No Forensic Sketch Rendered</h4>
        <p className="empty-desc">
          Render a clean 1024×1024 monochrome pencil portrait of the active Blender 3D character.
        </p>
        {onRenderSketch && (
          <button
            type="button"
            className="btn btn-primary btn-sm btn-generate-sketch"
            onClick={onRenderSketch}
            disabled={disabled}
          >
            Generate Forensic Sketch
          </button>
        )}
      </div>
    )
  }

  const imageUrl = sketchResult.image_url
    ? `${API_BASE_URL}${sketchResult.image_url}`
    : ''
  const formattedSize = sketchResult.filesize_bytes
    ? `${(sketchResult.filesize_bytes / 1024).toFixed(1)} KB`
    : 'Unknown size'

  return (
    <div className="card sketch-viewer-card">
      <div className="preview-header-row">
        <div className="preview-title-group">
          <span className="badge badge-success">FORENSIC SKETCH</span>
          <span className="badge badge-neutral">1024 × 1024 PNG</span>
          <span className="badge badge-subtle">85mm Portrait</span>
        </div>
        <div className="sketch-header-actions">
          {onRenderSketch && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={onRenderSketch}
              disabled={disabled}
              title="Re-render sketch from current Blender state"
            >
              Re-render
            </button>
          )}
          {imageUrl && (
            <a
              href={imageUrl}
              download={sketchResult.filename || 'forensic_sketch.png'}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm btn-primary btn-download"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                stroke="currentColor"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>Download</span>
            </a>
          )}
        </div>
      </div>

      {/* Portrait Image Frame */}
      <div className="sketch-portrait-frame">
        <img
          src={imageUrl}
          alt={`Forensic Sketch - ${sketchResult.character_name}`}
          className="sketch-portrait-img"
          width={1024}
          height={1024}
          loading="lazy"
          decoding="async"
        />
      </div>

      {/* Sketch Metadata Grid */}
      <div className="sketch-meta-grid">
        <div className="sketch-meta-item">
          <span className="sketch-meta-label">Subject:</span>
          <span className="sketch-meta-value">{sketchResult.character_name}</span>
        </div>
        <div className="sketch-meta-item">
          <span className="sketch-meta-label">Case ID:</span>
          <span className="sketch-meta-value">{sketchResult.case_id || 'Unassigned'}</span>
        </div>
        <div className="sketch-meta-item">
          <span className="sketch-meta-label">Dimensions:</span>
          <span className="sketch-meta-value">1024 × 1024 px</span>
        </div>
        <div className="sketch-meta-item">
          <span className="sketch-meta-label">File Size:</span>
          <span className="sketch-meta-value">{formattedSize}</span>
        </div>
      </div>

      <div className="sketch-footer-note">
        <span>Monochrome graphite contour portrait rendered directly from Blender 5.2 via Workbench cavity shading and offline PIL filtering.</span>
      </div>
    </div>
  )
}

