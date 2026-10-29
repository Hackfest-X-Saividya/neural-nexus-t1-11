import React from 'react'
import type { LiveStateResponse, HealthResponse } from '../types/api'

interface HeaderProps {
  health: HealthResponse | null
  blenderState: LiveStateResponse | null
  isCheckingBlender: boolean
  backendError: string | null
  onRefreshStatus: () => void
}

export const Header: React.FC<HeaderProps> = ({
  health,
  blenderState,
  isCheckingBlender,
  backendError,
  onRefreshStatus,
}) => {
  const isBlenderConnected = blenderState?.blender_available === true
  const isBackendHealthy = health?.status === 'healthy' && !backendError

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-logo-badge">
          <svg
            className="brand-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2a5 5 0 0 0-5 5v3a5 5 0 0 0 10 0V7a5 5 0 0 0-5-5z" />
            <path d="M7 10v1a5 5 0 0 0 10 0v-1" />
            <path d="M12 17v4" />
            <path d="M8 21h8" />
            <circle cx="10" cy="8" r="1" fill="currentColor" />
            <circle cx="14" cy="8" r="1" fill="currentColor" />
          </svg>
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">CrimeSketchAI</h1>
            <span className="badge badge-neutral">Studio v0.1</span>
          </div>
          <p className="brand-subtitle">
            Forensic Facial Reconstruction &amp; 3D Biometric Workspace
          </p>
        </div>
      </div>

      <div className="header-status-panel">
        {/* Backend API Status */}
        <div className="status-pill" title="FastAPI Refinement Backend Status">
          <span
            className={`status-dot ${isBackendHealthy ? 'dot-online' : 'dot-offline'}`}
          />
          <div className="status-text">
            <span className="status-label">Backend API</span>
            <span className="status-value">
              {isBackendHealthy
                ? `Online (v${health?.version || '0.1.0'})`
                : 'Offline / Error'}
            </span>
          </div>
        </div>

        {/* Blender MPFB Bridge Status */}
        <div
          className="status-pill"
          title={
            isBlenderConnected
              ? `Connected to MPFB Bridge at 127.0.0.1:9877 (${blenderState?.character_name})`
              : blenderState?.error_details || 'Blender bridge unavailable'
          }
        >
          <span
            className={`status-dot ${
              isCheckingBlender
                ? 'dot-checking'
                : isBlenderConnected
                ? 'dot-online'
                : 'dot-offline'
            }`}
          />
          <div className="status-text">
            <span className="status-label">Blender 5.2 Bridge</span>
            <span className="status-value">
              {isCheckingBlender
                ? 'Checking...'
                : isBlenderConnected
                ? `Connected (${blenderState?.character_name || 'Human'})`
                : 'Disconnected'}
            </span>
          </div>
        </div>

        <button
          className="btn-icon"
          onClick={onRefreshStatus}
          disabled={isCheckingBlender}
          title="Refresh connection status"
          aria-label="Refresh status"
        >
          <svg
            className={`icon-spin-on-load ${isCheckingBlender ? 'spinning' : ''}`}
            viewBox="0 0 24 24"
            width="16"
            height="16"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
          </svg>
        </button>
      </div>
    </header>
  )
}

