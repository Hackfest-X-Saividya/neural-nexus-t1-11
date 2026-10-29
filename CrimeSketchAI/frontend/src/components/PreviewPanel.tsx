import React from 'react'
import type { RefinementResponse, RefinementApplyResponse, SketchRenderResponse } from '../types/api'
import { SketchViewer } from './SketchViewer'

interface PreviewPanelProps {
  preview: RefinementResponse | null
  applyResult?: RefinementApplyResponse | null
  isLoading: boolean
  loadingStage?: 'refining' | 'applying' | null
  networkError: string | null
  sketchResult?: SketchRenderResponse | null
  isRenderingSketch?: boolean
  sketchError?: string | null
  onRenderSketch?: () => void
}

export const PreviewPanel: React.FC<PreviewPanelProps> = ({
  preview,
  applyResult,
  isLoading,
  loadingStage,
  networkError,
  sketchResult,
  isRenderingSketch = false,
  sketchError,
  onRenderSketch,
}) => {
  if (isLoading) {
    const isApplying = loadingStage === 'applying'
    return (
      <div className="card preview-card loading-state">
        <div className="spinner-lg" />
        <h3 className="loading-title">
          {isApplying ? 'Applying Changes to Blender...' : 'Analyzing Witness Description...'}
        </h3>
        <p className="loading-desc">
          {isApplying
            ? 'Sending set_targets command over MPFB bridge and verifying read-back target values.'
            : 'Analyzing witness description and computing biometric morph targets against live 3D model.'}
        </p>
      </div>
    )
  }

  if (networkError) {
    return (
      <div className="card preview-card error-card">
        <div className="state-badge-row">
          <span className="badge badge-danger">Connection Error</span>
        </div>
        <h3 className="error-title">Backend Server Unreachable</h3>
        <p className="error-body">{networkError}</p>
        <div className="troubleshoot-box">
          <strong>Troubleshooting steps:</strong>
          <ul>
            <li>
              Verify that Uvicorn is running:{' '}
              <code>uvicorn backend.main:app --host 127.0.0.1 --port 8000</code>
            </li>
            <li>Ensure the backend is accessible at <code>http://127.0.0.1:8000</code></li>
          </ul>
        </div>
      </div>
    )
  }

  if (isRenderingSketch && !isLoading && !applyResult && !preview) {
    return (
      <SketchViewer
        sketchResult={null}
        isRenderingSketch={true}
        sketchError={null}
        onRenderSketch={onRenderSketch}
      />
    )
  }

  if (sketchError && !sketchResult && !applyResult && !preview) {
    return (
      <SketchViewer
        sketchResult={null}
        isRenderingSketch={false}
        sketchError={sketchError}
        onRenderSketch={onRenderSketch}
      />
    )
  }

  if (!preview && !applyResult) {
    if (sketchResult) {
      return (
        <SketchViewer
          sketchResult={sketchResult}
          isRenderingSketch={isRenderingSketch}
          sketchError={sketchError || null}
          onRenderSketch={onRenderSketch}
        />
      )
    }

    return (
      <div className="card preview-card empty-state">
        <div className="empty-state-icon">
          <svg
            viewBox="0 0 24 24"
            width="36"
            height="36"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
            <path d="M14 9h4" />
            <path d="M14 15h4" />
          </svg>
        </div>
        <h3 className="empty-title">No Active Refinement</h3>
        <p className="empty-desc">
          Enter a suspect facial adjustment command above and click{' '}
          <strong>Generate &amp; Apply</strong> to refine and update the Blender 3D character.
        </p>
      </div>
    )
  }

  // REJECTED PREVIEW STATE (Stopped before apply)
  if (preview && preview.status === 'REJECTED') {
    return (
      <div className="card preview-card rejected-card">
        <div className="preview-header-row">
          <div className="preview-title-group">
            <span className="badge badge-danger">REJECTED</span>
            <span className="badge badge-neutral">Blender Unmodified</span>
            {preview.parser_mode === 'ai' && (
              <span className="badge badge-subtle">
                AI: {preview.parser_model || 'qwen3:4b'}
              </span>
            )}
          </div>
          <span className="source-badge badge-neutral">
            Source: {preview.value_source}
          </span>
        </div>

        <h3 className="rejected-title">Refinement Request Rejected</h3>

        <div className="meta-box">
          <span className="meta-label">Original Request:</span>
          <p className="meta-text">&ldquo;{preview.input_text}&rdquo;</p>
        </div>

        <div className="error-callout">
          <strong>Reason for Rejection:</strong>
          <p>{preview.error_message || preview.message}</p>
        </div>

        <div className="troubleshoot-box">
          <strong>Workflow Halted:</strong>
          <p>
            The refinement request was rejected during validation. No modifications were sent
            to Blender or executed on character &quot;Human&quot;.
          </p>
        </div>
      </div>
    )
  }

  // APPLY RESULT STATE (Successful or Failed Live Application)
  if (applyResult) {
    const isSuccess = applyResult.status === 'APPLIED' && applyResult.verified === true
    const isBilateral =
      applyResult.left_applied_value !== null &&
      applyResult.left_applied_value !== undefined

    return (
      <div className="preview-stack-layout">
        {sketchResult && (
          <SketchViewer
            sketchResult={sketchResult}
            isRenderingSketch={isRenderingSketch}
            sketchError={sketchError || null}
            onRenderSketch={onRenderSketch}
          />
        )}
        <div className={`card preview-card ${isSuccess ? 'ready-card' : 'rejected-card'}`}>
          {/* Header Badges */}
        <div className="preview-header-row">
          <div className="preview-title-group">
            <span className={`badge ${isSuccess ? 'badge-success' : 'badge-danger'}`}>
              {isSuccess ? 'BLENDER UPDATED' : 'APPLY FAILED'}
            </span>
            <span className={`badge ${applyResult.verified ? 'badge-success' : 'badge-danger'}`}>
              {applyResult.verified ? 'Verified Read-Back' : 'Verification Incomplete'}
            </span>
            {preview?.parser_mode === 'ai' ? (
              <span className="badge badge-subtle">
                AI: {preview.parser_model || 'qwen3:4b'}
              </span>
            ) : (
              <span className="badge badge-neutral">Rule-Based</span>
            )}
          </div>
          <span className="source-badge badge-live-source">
            <span className="dot-live" /> Character: {applyResult.character_name || 'Human'}
          </span>
        </div>

        {/* Title */}
        <h3 className={isSuccess ? 'feature-display-name feature-title-spaced' : 'rejected-title rejected-title-spaced'}>
          {isSuccess
            ? `Successfully Applied: ${applyResult.display_name || preview?.display_name}`
            : 'Application to Blender Failed'}
        </h3>

        {/* Compact Summary Grid */}
        <div className="metrics-triad-grid">
          <div className="metric-box">
            <span className="metric-label">AI Interpretation</span>
            <span className="metric-number metric-text-wrap">
              {applyResult.display_name || preview?.display_name}
            </span>
            <span className="metric-sub">Feature ID: {applyResult.feature_id || preview?.feature_id}</span>
          </div>

          <div className="metric-box">
            <span className="metric-label">Blender Updated?</span>
            <span
              className="metric-number"
              style={{
                fontSize: '1.05rem',
                color: isSuccess ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              }}
            >
              {isSuccess ? 'YES — Applied' : 'NO — Aborted'}
            </span>
            <span className="metric-sub">
              {isSuccess ? "Morph targets committed on 'Human'" : '3D scene unchanged'}
            </span>
          </div>

          <div className="metric-box metric-box-accent">
            <span className="metric-label">Read-Back Verification</span>
            <span
              className="metric-number"
              style={{
                fontSize: '1.05rem',
                color: applyResult.verified ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              }}
            >
              {applyResult.verified ? 'PASSED (±0.001)' : 'FAILED'}
            </span>
            <span className="metric-sub">
              {applyResult.verified
                ? 'Unrelated features unchanged'
                : 'Values did not match or drifted'}
            </span>
          </div>
        </div>

        {/* Value Changes / Progression */}
        {isSuccess && (
          <>
            {applyResult.features_applied && applyResult.features_applied.length > 1 ? (
              <div className="table-responsive" style={{ marginBottom: '1rem' }}>
                <table className="payload-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Type</th>
                      <th>Previous Value</th>
                      <th>Live Applied</th>
                      <th>Verification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applyResult.features_applied.map((f: any, idx: number) => {
                      const isSided = f.is_sided
                      return (
                        <tr key={idx}>
                          <td style={{ color: 'var(--text-main)', fontWeight: 600 }}>{f.display_name}</td>
                          <td>
                            <span className="side-badge">{isSided ? 'Bilateral (L/R)' : 'Unsided'}</span>
                          </td>
                          <td>
                            {isSided ? (
                              <>L: {f.previous_left_value?.toFixed(2)} | R: {f.previous_right_value?.toFixed(2)}</>
                            ) : (
                              <>{(f.previous_value || 0) >= 0 ? '+' : ''}{f.previous_value?.toFixed(2)}</>
                            )}
                          </td>
                          <td className="table-val-cell">
                            {isSided ? (
                              <>L: {f.applied_left_value?.toFixed(2)} | R: {f.applied_right_value?.toFixed(2)}</>
                            ) : (
                              <>{(f.applied_value || 0) >= 0 ? '+' : ''}{f.applied_value?.toFixed(2)}</>
                            )}
                          </td>
                          <td style={{ color: f.verified ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 600 }}>
                            {f.verified ? '✓ Verified' : '✗ Failed'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : isBilateral ? (
              <div className="bilateral-comparison-grid" style={{ marginBottom: '1rem' }}>
                <div className="side-card">
                  <div className="side-card-header">
                    <span className="side-tag">Left Side</span>
                  </div>
                  <div className="side-values-row">
                    <div className="val-block">
                      <span className="val-label">Previous</span>
                      <span className="val-num">
                        {(applyResult.left_previous_value || 0) >= 0 ? '+' : ''}
                        {applyResult.left_previous_value?.toFixed(2)}
                      </span>
                    </div>
                    <span className="arrow-icon">&rarr;</span>
                    <div className="val-block">
                      <span className="val-label">Live Applied</span>
                      <span className="val-num val-proposed">
                        {(applyResult.left_applied_value || 0) >= 0 ? '+' : ''}
                        {applyResult.left_applied_value?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="side-card">
                  <div className="side-card-header">
                    <span className="side-tag">Right Side</span>
                  </div>
                  <div className="side-values-row">
                    <div className="val-block">
                      <span className="val-label">Previous</span>
                      <span className="val-num">
                        {(applyResult.right_previous_value || 0) >= 0 ? '+' : ''}
                        {applyResult.right_previous_value?.toFixed(2)}
                      </span>
                    </div>
                    <span className="arrow-icon">&rarr;</span>
                    <div className="val-block">
                      <span className="val-label">Live Applied</span>
                      <span className="val-num val-proposed">
                        {(applyResult.right_applied_value || 0) >= 0 ? '+' : ''}
                        {applyResult.right_applied_value?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="metrics-triad-grid" style={{ marginBottom: '1rem' }}>
                <div className="metric-box">
                  <span className="metric-label">Previous Value</span>
                  <span className="metric-number">
                    {(applyResult.previous_value || 0) >= 0 ? '+' : ''}
                    {applyResult.previous_value?.toFixed(2)}
                  </span>
                  <span className="metric-sub">Before mutation</span>
                </div>

                <div className="metric-box">
                  <span className="metric-label">Adjustment Delta</span>
                  <span
                    className={`metric-number ${
                      (preview?.proposed_delta || 0) >= 0 ? 'delta-pos' : 'delta-neg'
                    }`}
                  >
                    {(preview?.proposed_delta || 0) >= 0
                      ? `+${preview?.proposed_delta}`
                      : preview?.proposed_delta}
                  </span>
                  <span className="metric-sub">Proposed adjustment</span>
                </div>

                <div className="metric-box metric-box-accent">
                  <span className="metric-label">Live Applied Value</span>
                  <span className="metric-number val-proposed">
                    {(applyResult.applied_value || 0) >= 0 ? '+' : ''}
                    {applyResult.applied_value?.toFixed(2)}
                  </span>
                  <span className="metric-sub">Confirmed in Blender</span>
                </div>
              </div>
            )}
          </>
        )}

        {/* Applied Asset Adjustments (Hair / Eyebrows) */}
        {applyResult.assets_applied && applyResult.assets_applied.length > 0 && (
          <div className="asset-adjustments-card" style={{ marginBottom: '1rem', background: 'var(--bg-subtle, #1e293b)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>Equipped Assets Modified</span>
              <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>{applyResult.assets_applied.length} Asset{applyResult.assets_applied.length > 1 ? 's' : ''}</span>
            </h4>
            <div className="asset-tags-row" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {applyResult.assets_applied.map((a: any, idx: number) => {
                const isRemoval = a.action === 'remove'
                return (
                  <div
                    key={idx}
                    className="metric-box"
                    style={{
                      flex: '1 1 200px',
                      padding: '0.6rem 0.85rem',
                      background: 'rgba(15, 23, 42, 0.6)',
                      borderRadius: '6px',
                      border: '1px solid rgba(255, 255, 255, 0.08)'
                    }}
                  >
                    <span className="metric-label" style={{ fontSize: '0.72rem', textTransform: 'capitalize' }}>
                      {a.asset_type === 'hair' ? 'Hairstyle' : 'Eyebrows'}
                    </span>
                    <div style={{ marginTop: '0.2rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {isRemoval ? (
                        <span style={{ color: 'var(--accent-amber)' }}>Bald (Removed)</span>
                      ) : (
                        <span style={{ color: 'var(--accent-emerald)' }}>{a.display_name || a.asset_id}</span>
                      )}
                    </div>
                    <div style={{ marginTop: '0.2rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Object: <code>{a.applied_asset_name || a.removed_asset_name || 'None'}</code>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Instruction and Outcome Message */}
        <div className="meta-box" style={{ marginBottom: '0.75rem' }}>
          <span className="meta-label">Original Request:</span>
          <p className="meta-text">&ldquo;{preview?.input_text}&rdquo;</p>
        </div>

        {isSuccess ? (
          <div className="preview-summary-card" style={{ marginBottom: '0.75rem' }}>
            <p className="preview-message-text">{applyResult.message}</p>
          </div>
        ) : (
          <div className="error-callout" style={{ marginBottom: '0.75rem' }}>
            <strong>Failure Details:</strong>
            <p>{applyResult.error_message || applyResult.message}</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              If a state drift occurred, click <strong>Generate &amp; Apply</strong> again to submit a
              fresh adjustment against the current live Blender state.
            </p>
          </div>
        )}

        {/* Footer info */}
        <div className="preview-safety-footer">
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
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span>
            {isSuccess
              ? `Live Apply Confirmed: Audit record #${applyResult.apply_log_id} recorded in SQLite.`
              : `Application Failed: Rejection record #${applyResult.apply_log_id || 'N/A'} logged.`}
          </span>
        </div>
      </div>
    </div>
    )
  }

  // PREVIEW ONLY STATE (When user selected "Preview Only")
  const isLive = preview?.value_source === 'live_blender'
  const isBilateral =
    preview?.left_proposed_value !== undefined &&
    preview?.left_proposed_value !== null &&
    preview?.right_proposed_value !== undefined &&
    preview?.right_proposed_value !== null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {sketchResult && (
        <SketchViewer
          sketchResult={sketchResult}
          isRenderingSketch={isRenderingSketch}
          sketchError={sketchError || null}
          onRenderSketch={onRenderSketch}
        />
      )}
      <div className="card preview-card ready-card">
      {/* Top Banner */}
      <div className="preview-header-row">
        <div className="preview-title-group">
          <span className="badge badge-success">PREVIEW READY</span>
          <span className="badge badge-dryrun">Preview Only (Not Applied)</span>
          {preview?.parser_mode === 'ai' ? (
            <span className="badge badge-subtle">
              AI: {preview?.parser_model || 'qwen3:4b'}
            </span>
          ) : (
            <span className="badge badge-neutral">Rule-Based</span>
          )}
        </div>
        <span
          className={`source-badge ${isLive ? 'badge-live-source' : 'badge-cached-source'}`}
        >
          {isLive ? (
            <>
              <span className="dot-live" /> Live Blender Read
            </>
          ) : (
            'Offline Cached Reference'
          )}
        </span>
      </div>

      {/* Feature & Instruction Info */}
      <div className="preview-summary-card">
        <div className="feature-meta-header">
          <div>
            <h3 className="feature-display-name">{preview?.display_name}</h3>
            <span className="feature-id-code">ID: {preview?.feature_id}</span>
          </div>
          <div className="delta-badge">
            <span className="delta-label">Delta:</span>
            <span
              className={`delta-value ${
                (preview?.proposed_delta || 0) >= 0 ? 'delta-pos' : 'delta-neg'
              }`}
            >
              {(preview?.proposed_delta || 0) >= 0
                ? `+${preview?.proposed_delta}`
                : preview?.proposed_delta}
            </span>
          </div>
        </div>

        <p className="preview-instruction-quote">&ldquo;{preview?.input_text}&rdquo;</p>
        <p className="preview-message-text">{preview?.message}</p>
      </div>

      {/* Value Progression Cards */}
      {preview?.features && preview.features.length > 1 ? (
        <div className="table-responsive" style={{ marginBottom: '1.25rem' }}>
          <table className="payload-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Type</th>
                <th>Delta</th>
                <th>Baseline</th>
                <th>Proposed</th>
                <th>Bounds</th>
              </tr>
            </thead>
            <tbody>
              {preview.features.map((f, idx) => (
                <tr key={idx}>
                  <td style={{ color: 'var(--text-main)', fontWeight: 600 }}>{f.display_name}</td>
                  <td>
                    <span className="side-badge">{f.is_sided ? 'Bilateral' : 'Unsided'}</span>
                  </td>
                  <td className={f.adjustment_delta >= 0 ? 'delta-pos' : 'delta-neg'}>
                    {f.adjustment_delta >= 0 ? `+${f.adjustment_delta}` : f.adjustment_delta}
                  </td>
                  <td>
                    {f.is_sided ? (
                      <>L: {f.left_current_value?.toFixed(2)} | R: {f.right_current_value?.toFixed(2)}</>
                    ) : (
                      <>{(f.current_value || 0) >= 0 ? '+' : ''}{f.current_value?.toFixed(2)}</>
                    )}
                  </td>
                  <td className="table-val-cell">
                    {f.is_sided ? (
                      <>L: {f.left_proposed_value?.toFixed(2)} | R: {f.right_proposed_value?.toFixed(2)}</>
                    ) : (
                      <>{(f.proposed_value || 0) >= 0 ? '+' : ''}{f.proposed_value?.toFixed(2)}</>
                    )}
                  </td>
                  <td>
                    {f.is_boundary_clamped ? (
                      <span style={{ color: 'var(--accent-amber)', fontSize: '0.75rem' }}>Clamped</span>
                    ) : (
                      <span style={{ color: 'var(--accent-emerald)', fontSize: '0.75rem' }}>Within Bounds</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : isBilateral ? (
        <div className="bilateral-comparison-grid">
          <div className="side-card">
            <div className="side-card-header">
              <span className="side-tag">Left Side</span>
              {preview?.is_symmetric !== null && (
                <span
                  className={`badge ${
                    preview?.is_symmetric ? 'badge-neutral' : 'badge-amber'
                  }`}
                >
                  {preview?.is_symmetric ? 'Symmetric' : 'Asymmetric (Preserved)'}
                </span>
              )}
            </div>
            <div className="side-values-row">
              <div className="val-block">
                <span className="val-label">
                  {isLive ? 'Live Current' : 'Cached Baseline'}
                </span>
                <span className="val-num">
                  {(preview?.left_current_value || 0) >= 0 ? '+' : ''}
                  {preview?.left_current_value?.toFixed(2)}
                </span>
              </div>
              <span className="arrow-icon">&rarr;</span>
              <div className="val-block">
                <span className="val-label">Proposed</span>
                <span className="val-num val-proposed">
                  {(preview?.left_proposed_value || 0) >= 0 ? '+' : ''}
                  {preview?.left_proposed_value?.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="side-card">
            <div className="side-card-header">
              <span className="side-tag">Right Side</span>
              {preview?.is_symmetric !== null && (
                <span
                  className={`badge ${
                    preview?.is_symmetric ? 'badge-neutral' : 'badge-amber'
                  }`}
                >
                  {preview?.is_symmetric ? 'Symmetric' : 'Asymmetric (Preserved)'}
                </span>
              )}
            </div>
            <div className="side-values-row">
              <div className="val-block">
                <span className="val-label">
                  {isLive ? 'Live Current' : 'Cached Baseline'}
                </span>
                <span className="val-num">
                  {(preview?.right_current_value || 0) >= 0 ? '+' : ''}
                  {preview?.right_current_value?.toFixed(2)}
                </span>
              </div>
              <span className="arrow-icon">&rarr;</span>
              <div className="val-block">
                <span className="val-label">Proposed</span>
                <span className="val-num val-proposed">
                  {(preview?.right_proposed_value || 0) >= 0 ? '+' : ''}
                  {preview?.right_proposed_value?.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="metrics-triad-grid">
          <div className="metric-box">
            <span className="metric-label">
              {isLive ? 'Observed Current (Live)' : 'Cached Reference Value'}
            </span>
            <span className="metric-number">
              {(preview?.current_value || 0) >= 0 ? '+' : ''}
              {preview?.current_value?.toFixed(2)}
            </span>
            <span className="metric-sub">
              {isLive ? 'Read from Blender' : 'Offline baseline'}
            </span>
          </div>

          <div className="metric-box">
            <span className="metric-label">Adjustment Amount</span>
            <span
              className={`metric-number ${
                (preview?.proposed_delta || 0) >= 0 ? 'delta-pos' : 'delta-neg'
              }`}
            >
              {(preview?.proposed_delta || 0) >= 0
                ? `+${preview?.proposed_delta}`
                : preview?.proposed_delta}
            </span>
            <span className="metric-sub">Verified step size</span>
          </div>

          <div className="metric-box metric-box-accent">
            <span className="metric-label">Proposed Target Value</span>
            <span className="metric-number val-proposed">
              {(preview?.proposed_value || 0) >= 0 ? '+' : ''}
              {preview?.proposed_value?.toFixed(2)}
            </span>
            <span className="metric-sub">Simulated slider value</span>
          </div>
        </div>
      )}

      {/* Proposed Asset Adjustments (Hair / Eyebrows) */}
      {preview?.asset_adjustments && preview.asset_adjustments.length > 0 && (
        <div className="asset-adjustments-card" style={{ marginBottom: '1.25rem', background: 'var(--bg-subtle, #1e293b)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>Proposed Asset Customizations</span>
            <span className="badge badge-subtle" style={{ fontSize: '0.75rem' }}>{preview.asset_adjustments.length}</span>
          </h4>
          <div className="asset-adjustments-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
            {preview.asset_adjustments.map((a, idx) => {
              const isRemoval = a.action === 'remove' || !a.proposed_asset_id
              return (
                <div key={idx} className="metric-box" style={{ textAlign: 'left', padding: '0.65rem 0.85rem', background: 'rgba(15, 23, 42, 0.6)' }}>
                  <span className="metric-label" style={{ fontSize: '0.72rem', textTransform: 'capitalize' }}>
                    {a.asset_type === 'hair' ? 'Hairstyle' : 'Eyebrows'}
                  </span>
                  <div style={{ marginTop: '0.2rem', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
                    {isRemoval ? (
                      <span style={{ color: 'var(--accent-amber)' }}>Remove (Bald)</span>
                    ) : (
                      <span style={{ color: 'var(--accent-emerald)' }}>{a.proposed_display_name}</span>
                    )}
                  </div>
                  <div style={{ marginTop: '0.2rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Action: <span style={{ textTransform: 'capitalize' }}>{a.action}</span>
                    {a.current_asset_name && ` | Current: ${a.current_asset_name}`}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Target Identifiers & Shape Keys */}
      <div className="target-details-section">
        <div className="target-item-group">
          <span className="target-group-label">Target Identifiers:</span>
          <div className="target-tags-row">
            {preview?.target_identifiers.map((tid) => (
              <span key={tid} className="target-tag">
                {tid}
              </span>
            ))}
          </div>
        </div>

        <div className="target-item-group">
          <span className="target-group-label">Target Shape Keys:</span>
          <div className="target-tags-row">
            {preview?.target_shapekeys.map((sk) => (
              <span key={sk} className="target-tag shapekey-tag">
                {sk}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Safety Notice Footer */}
      <div className="preview-safety-footer">
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
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <span>
          <strong>Dry-Run Preview Only:</strong> Click <strong>Generate &amp; Apply</strong> to apply
          these modifications to the active 3D character in Blender.
        </span>
      </div>
    </div>
    </div>
  )
}
