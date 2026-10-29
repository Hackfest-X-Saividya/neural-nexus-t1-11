import React, { useState } from 'react'
import type { LiveStateResponse, HealthResponse } from '../types/api'

interface RefinementFormProps {
  onGenerateAndApply?: (params: {
    text: string
    caseId: string
    characterName: string
    parserMode?: 'rule_based' | 'ai'
  }) => void
  onRefine?: (params: {
    text: string
    caseId: string
    characterName: string
    useLiveState: boolean
    parserMode?: 'rule_based' | 'ai'
  }) => void
  onPreviewOnly?: (params: {
    text: string
    caseId: string
    characterName: string
    useLiveState: boolean
    parserMode?: 'rule_based' | 'ai'
  }) => void
  onRenderSketch?: (params: {
    caseId: string
    characterName: string
  }) => void
  isRenderingSketch?: boolean
  isLoading: boolean
  loadingStage?: 'refining' | 'applying' | null
  blenderState: LiveStateResponse | null
  health?: HealthResponse | null
}

const EXAMPLE_COMMANDS = [
  'Make the cheekbones more prominent.',
  'Make the nose slightly wider.',
  'A suspect with an afro and a wide jaw.',
  'Make the lips fuller with a defined cupid\'s bow.',
  'Make the jaw wider and more square.',
  'Change the hairstyle to a bob cut.',
  'Make the suspect bald with thick eyebrows.',
  'A person with a neat side-parted haircut, thin curved eyebrows, and prominent cheekbones.',
  'A person with a broad nose, prominent cheekbones, a slightly pointed chin, small eyes, and a narrow face.',
  'Make the nose slightly narrower.',
  'Add a prominent dorsal hump to the nose.',
  'Make the ears slightly more protruding.',
  'Make the eyelids hooded with subtle eye bags.',
  'Increase the chin prominence slightly.',
  'Make the eyes slightly larger.',
  'Make the forehead taller.',
  'Make the head wider.',
  'Make the mouth slightly narrower.',
]

export const RefinementForm: React.FC<RefinementFormProps> = ({
  onGenerateAndApply,
  onRefine,
  onPreviewOnly,
  onRenderSketch,
  isRenderingSketch = false,
  isLoading,
  loadingStage,
  blenderState,
  health,
}) => {
  const [text, setText] = useState('Make the nose slightly wider.')
  const [caseId, setCaseId] = useState('CASE-2026-001')
  const [characterName, setCharacterName] = useState('Human')
  const [useLiveState, setUseLiveState] = useState(true)
  const [parserMode, setParserMode] = useState<'rule_based' | 'ai'>('ai')
  const [showAllPresets, setShowAllPresets] = useState(false)

  const isBlenderOnline = blenderState?.blender_available === true
  const isOllamaOnline = health?.ollama_available === true

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim() || isLoading) return

    if (onGenerateAndApply) {
      onGenerateAndApply({
        text: text.trim(),
        caseId: caseId.trim(),
        characterName: characterName.trim(),
        parserMode,
      })
    } else if (onRefine) {
      onRefine({
        text: text.trim(),
        caseId: caseId.trim(),
        characterName: characterName.trim(),
        useLiveState: true,
        parserMode,
      })
    }
  }

  const handlePreviewClick = (e: React.MouseEvent) => {
    e.preventDefault()
    if (!text.trim() || isLoading) return

    if (onPreviewOnly) {
      onPreviewOnly({
        text: text.trim(),
        caseId: caseId.trim(),
        characterName: characterName.trim(),
        useLiveState,
        parserMode,
      })
    } else if (onRefine) {
      onRefine({
        text: text.trim(),
        caseId: caseId.trim(),
        characterName: characterName.trim(),
        useLiveState,
        parserMode,
      })
    }
  }

  return (
    <div className="card workspace-form-card">
      <div className="card-header">
        <div className="card-title-group">
          <h2 className="card-title">Refinement Workspace</h2>
          <span className="badge badge-success">Live Blender Apply</span>
        </div>
        <p className="card-description">
          Describe witness observations in plain English to adjust facial geometry,
          hairstyle, and eyebrows on the 3D character in Blender.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="refinement-form">
        {/* Character & Case ID Row */}
        <div className="form-row form-row-2">
          <div className="form-group">
            <label htmlFor="character-select" className="form-label">
              Character Model
            </label>
            <select
              id="character-select"
              className="form-input"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              disabled={isLoading}
            >
              <option value="Human">Human (Active 3D Subject)</option>
            </select>
            <span className="field-hint">
              Target subject in the active Blender scene (strictly &quot;Human&quot;)
            </span>
          </div>

          <div className="form-group">
            <label htmlFor="case-id-input" className="form-label">
              Case Identifier (Optional)
            </label>
            <input
              id="case-id-input"
              type="text"
              className="form-input"
              placeholder="e.g. CASE-2026-001"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              disabled={isLoading}
            />
            <span className="field-hint">
              Logged to SQLite audit records for forensic chain-of-custody
            </span>
          </div>
        </div>

        {/* State Mode Selection */}
        <div className="form-group" role="radiogroup" aria-labelledby="reference-source-label">
          <label id="reference-source-label" className="form-label">
            Refinement Reference Source
          </label>
          <div className="mode-toggle-grid">
            <label
              className={`mode-option-card ${
                useLiveState ? 'mode-option-selected' : ''
              } ${!isBlenderOnline ? 'mode-option-warning' : ''}`}
            >
              <input
                type="radio"
                name="refinement-mode"
                checked={useLiveState}
                onChange={() => setUseLiveState(true)}
                disabled={isLoading}
              />
              <div className="mode-card-content">
                <div className="mode-card-title-row">
                  <span className="mode-title">Live Blender Target Stack</span>
                  <span
                    className={`badge ${
                      isBlenderOnline ? 'badge-success' : 'badge-danger'
                    }`}
                  >
                    {isBlenderOnline ? 'Live Inspection' : 'Bridge Required'}
                  </span>
                </div>
                <p className="mode-desc">
                  Queries active target values from Blender via MPFB Bridge port 9877.
                  Required for live application.
                </p>
              </div>
            </label>

            <label
              className={`mode-option-card ${
                !useLiveState ? 'mode-option-selected' : ''
              }`}
            >
              <input
                type="radio"
                name="refinement-mode"
                checked={!useLiveState}
                onChange={() => setUseLiveState(false)}
                disabled={isLoading}
              />
              <div className="mode-card-content">
                <div className="mode-card-title-row">
                  <span className="mode-title">Cached Reference Baseline</span>
                  <span className="badge badge-neutral">Preview Only</span>
                </div>
                <p className="mode-desc">
                  Uses verified offline model reference values. Cannot be applied to Blender.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Refinement Parser Selection */}
        <div className="form-group" role="radiogroup" aria-labelledby="parser-mode-label">
          <label id="parser-mode-label" className="form-label">
            Command Interpreter (Parser Mode)
          </label>
          <div className="mode-toggle-grid">
            <label
              className={`mode-option-card ${
                parserMode === 'ai' ? 'mode-option-selected' : ''
              }`}
            >
              <input
                type="radio"
                name="parser-mode"
                checked={parserMode === 'ai'}
                onChange={() => setParserMode('ai')}
                disabled={isLoading}
              />
              <div className="mode-card-content">
                <div className="mode-card-title-row">
                  <span className="mode-title">Natural Language Parser</span>
                  <span
                    className={`badge ${
                      isOllamaOnline ? 'badge-subtle' : 'badge-neutral'
                    }`}
                  >
                    {health?.ollama_model || 'qwen3:4b'}
                  </span>
                </div>
                <p className="mode-desc">
                  Context-aware semantic parsing of witness descriptions into 3D facial morph controls.
                </p>
              </div>
            </label>

            <label
              className={`mode-option-card ${
                parserMode === 'rule_based' ? 'mode-option-selected' : ''
              }`}
            >
              <input
                type="radio"
                name="parser-mode"
                checked={parserMode === 'rule_based'}
                onChange={() => setParserMode('rule_based')}
                disabled={isLoading}
              />
              <div className="mode-card-content">
                <div className="mode-card-title-row">
                  <span className="mode-title">Rule-Based Parser</span>
                  <span className="badge badge-neutral">Deterministic</span>
                </div>
                <p className="mode-desc">
                  Deterministic keyword and regex allowlist mapping.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Natural Language Instruction */}
        <div className="form-group">
          <div className="label-with-meta">
            <label htmlFor="refinement-text" className="form-label">
              Natural-Language Refinement Command
            </label>
            <span className="text-counter">{text.length} chars</span>
          </div>
          <textarea
            id="refinement-text"
            className="form-textarea"
            rows={3}
            placeholder="e.g. Make the nose slightly wider."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={isLoading}
            required
          />
        </div>

        {/* Quick Example Chips */}
        <div className="example-chips-container">
          <div className="chips-header-row">
            <span className="chips-label">Witness Description Presets</span>
            <button
              type="button"
              className="chips-toggle-btn"
              onClick={() => setShowAllPresets(!showAllPresets)}
              disabled={isLoading}
            >
              {showAllPresets ? 'Show Fewer' : `+ ${EXAMPLE_COMMANDS.length - 5} More Presets`}
            </button>
          </div>
          <div className={`chips-list ${showAllPresets ? 'chips-expanded' : 'chips-collapsed'}`}>
            {EXAMPLE_COMMANDS.map((cmd) => (
              <button
                key={cmd}
                type="button"
                className="chip-btn"
                onClick={() => setText(cmd)}
                disabled={isLoading}
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>

        {/* Actions & Live Apply Button */}
        <div className="form-actions-bar">
          <div className="dry-run-notice">
            <svg
              className="notice-icon"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>
              <strong>1-Click Live Apply:</strong> Interprets witness description, verifies live state,
              and applies changes directly to &quot;Human&quot; in Blender.
            </span>
          </div>

          <div className="form-actions-buttons">
            {onRenderSketch && (
              <button
                type="button"
                className="btn btn-secondary btn-sketch-action"
                onClick={() => onRenderSketch({ caseId, characterName })}
                disabled={isLoading || isRenderingSketch}
                title="Render a 1024x1024 monochrome forensic pencil-sketch portrait from the live Blender character"
              >
                {isRenderingSketch ? (
                  <>
                    <span className="spinner-sm" />
                    <span>Rendering Sketch...</span>
                  </>
                ) : (
                  <>
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      stroke="currentColor"
                      strokeWidth="2"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                      <circle cx="12" cy="13" r="4" />
                    </svg>
                    <span>Generate Sketch</span>
                  </>
                )}
              </button>
            )}

            {onPreviewOnly && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handlePreviewClick}
                disabled={isLoading || !text.trim()}
              >
                Preview Only
              </button>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading || !text.trim()}
            >
              {isLoading ? (
                <>
                  <span className="spinner-sm" />
                  <span>
                    {loadingStage === 'applying'
                      ? 'Applying to Blender...'
                      : loadingStage === 'refining'
                      ? 'Interpreting Command...'
                      : 'Processing...'}
                  </span>
                </>
              ) : (
                <>
                  <svg
                    viewBox="0 0 24 24"
                    width="18"
                    height="18"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  <span>Generate &amp; Apply</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
