import React, { useState } from 'react'
import type { AuditLogEntry } from '../types/api'

interface AuditHistoryProps {
  logs: AuditLogEntry[]
  isLoading: boolean
  onRefresh: (caseId?: string) => void
  currentCaseId?: string
}

export const AuditHistory: React.FC<AuditHistoryProps> = ({
  logs,
  isLoading,
  onRefresh,
  currentCaseId,
}) => {
  const [filterCaseId, setFilterCaseId] = useState(currentCaseId || '')
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onRefresh(filterCaseId.trim() || undefined)
  }

  const handleClearFilter = () => {
    setFilterCaseId('')
    onRefresh(undefined)
  }

  return (
    <div className="card audit-card">
      <div className="card-header audit-header">
        <div>
          <h2 className="card-title">Forensic Audit Trail</h2>
          <p className="card-description">
            Complete chain-of-custody log of all refinement simulations and rejections
            recorded in SQLite (<code>refinements.db</code>).
          </p>
        </div>

        {/* Filter & Refresh Controls */}
        <form onSubmit={handleFilterSubmit} className="audit-controls-form">
          <div className="filter-input-group">
            <label htmlFor="audit-case-filter" className="sr-only">
              Filter by Case ID
            </label>
            <input
              id="audit-case-filter"
              type="text"
              className="form-input form-input-sm"
              placeholder="Filter by Case ID..."
              aria-label="Filter audit records by Case ID"
              value={filterCaseId}
              onChange={(e) => setFilterCaseId(e.target.value)}
            />
            {filterCaseId && (
              <button
                type="button"
                className="btn-clear"
                onClick={handleClearFilter}
                title="Clear filter"
                aria-label="Clear filter"
              >
                &times;
              </button>
            )}
          </div>
          <button
            type="submit"
            className="btn btn-secondary btn-sm"
            disabled={isLoading}
          >
            Filter
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onRefresh(filterCaseId.trim() || undefined)}
            disabled={isLoading}
            title="Refresh logs from database"
          >
            <span className={isLoading ? 'spinning' : ''}>&#x21bb;</span> Refresh
          </button>
        </form>
      </div>

      {logs.length === 0 ? (
        <div className="audit-empty-state">
          <p>No audit records found{filterCaseId ? ` for Case ID "${filterCaseId}"` : ''}.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="audit-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>UTC Timestamp</th>
                <th>Case ID</th>
                <th>Status</th>
                <th>Instruction</th>
                <th>Parsed Feature</th>
                <th>Current &rarr; Proposed</th>
                <th>Source</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                let details: any = null
                try {
                  if (log.details_json) {
                    details = JSON.parse(log.details_json)
                  }
                } catch {
                  // ignore JSON parse error
                }

                const isSuccess = log.status === 'PREVIEW_READY'
                const valueSource =
                  details?.value_source ||
                  details?.state_source ||
                  (details?.is_live_blender_value
                    ? 'live_blender'
                    : details?.use_live_state
                    ? 'unavailable'
                    : 'cached_reference')
                const isExpanded = expandedRow === log.id

                return (
                  <React.Fragment key={log.id}>
                    <tr
                      className={`audit-row ${
                        isSuccess ? 'audit-row-success' : 'audit-row-rejected'
                      }`}
                      tabIndex={0}
                      role="button"
                      aria-expanded={isExpanded}
                      onClick={() => setExpandedRow(isExpanded ? null : log.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          setExpandedRow(isExpanded ? null : log.id)
                        }
                      }}
                    >
                      <td className="font-mono text-muted">#{log.id}</td>
                      <td className="font-mono text-xs">
                        {log.timestamp_utc ? log.timestamp_utc.slice(0, 19).replace('T', ' ') : '—'}
                      </td>
                      <td>
                        <span className="case-id-badge">
                          {log.case_id || '—'}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isSuccess ? 'badge-success' : 'badge-danger'
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="log-text-cell" title={log.request_text}>
                        &ldquo;{log.request_text}&rdquo;
                      </td>
                      <td>
                        {log.parsed_feature ? (
                          <span className="feature-pill">{log.parsed_feature}</span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td className="font-mono text-xs">
                        {log.current_value !== null && log.proposed_value !== null ? (
                          <span>
                            {(log.current_value ?? 0) >= 0 ? '+' : ''}
                            {log.current_value?.toFixed(2)} &rarr;{' '}
                            {(log.proposed_value ?? 0) >= 0 ? '+' : ''}
                            {log.proposed_value?.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td>
                        <span
                          className={`source-mini-tag ${
                            valueSource === 'live_blender'
                              ? 'source-live'
                              : valueSource === 'unavailable'
                              ? 'source-unavailable'
                              : 'source-cached'
                          }`}
                        >
                          {valueSource === 'live_blender'
                            ? 'live'
                            : valueSource === 'unavailable'
                            ? 'unavailable'
                            : 'cached'}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn-link text-xs"
                          onClick={(e) => {
                            e.stopPropagation()
                            setExpandedRow(isExpanded ? null : log.id)
                          }}
                        >
                          {isExpanded ? 'Hide' : 'Inspect'}
                        </button>
                      </td>
                    </tr>

                    {/* Expanded Detail Accordion */}
                    {isExpanded && (
                      <tr className="audit-expanded-row">
                        <td colSpan={9}>
                          <div className="audit-detail-box">
                            <div className="detail-grid">
                              <div>
                                <strong>Target Identifier:</strong>{' '}
                                <code>{log.target_identifier || 'None'}</code>
                              </div>
                              <div>
                                <strong>Execution Mode:</strong>{' '}
                                <code>{log.mode}</code>
                              </div>
                              {log.error_message && (
                                <div className="detail-error-full">
                                  <strong>Error / Rejection Details:</strong>{' '}
                                  <span className="text-danger">
                                    {log.error_message}
                                  </span>
                                </div>
                              )}
                              {details?.boundary_warning && (
                                <div className="detail-warning-full">
                                  <strong>Boundary Clamping:</strong>{' '}
                                  <span className="text-warning">
                                    {details.boundary_warning}
                                  </span>
                                </div>
                              )}
                              {details?.target_shapekeys && (
                                <div>
                                  <strong>Target Shape Keys:</strong>{' '}
                                  <span>
                                    {details.target_shapekeys.join(', ')}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

