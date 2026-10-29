import { useState, useEffect, useCallback } from 'react'
import { api } from './api/client'
import type {
  HealthResponse,
  LiveStateResponse,
  RefinementResponse,
  RefinementApplyResponse,
  AuditLogEntry,
  SketchRenderResponse,
} from './types/api'
import { Header } from './components/Header'
import { RefinementForm } from './components/RefinementForm'
import { PreviewPanel } from './components/PreviewPanel'
import { AuditHistory } from './components/AuditHistory'
import './App.css'

export function App() {
  // Status states
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [blenderState, setBlenderState] = useState<LiveStateResponse | null>(null)
  const [isCheckingBlender, setIsCheckingBlender] = useState(false)
  const [backendError, setBackendError] = useState<string | null>(null)

  // Refinement workflow states
  const [preview, setPreview] = useState<RefinementResponse | null>(null)
  const [applyResult, setApplyResult] = useState<RefinementApplyResponse | null>(null)
  const [isExecutingWorkflow, setIsExecutingWorkflow] = useState(false)
  const [loadingStage, setLoadingStage] = useState<'refining' | 'applying' | null>(null)
  const [previewNetworkError, setPreviewNetworkError] = useState<string | null>(null)

  // Forensic sketch state
  const [sketchResult, setSketchResult] = useState<SketchRenderResponse | null>(null)
  const [isRenderingSketch, setIsRenderingSketch] = useState(false)
  const [sketchError, setSketchError] = useState<string | null>(null)

  // Audit logs state
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [currentCaseId, setCurrentCaseId] = useState('CASE-2026-001')

  // Check health and Blender state
  const refreshStatus = useCallback(async () => {
    setIsCheckingBlender(true)
    setBackendError(null)

    try {
      const [healthData, liveStateData] = await Promise.allSettled([
        api.getHealth(),
        api.getLiveState('Human'),
      ])

      if (healthData.status === 'fulfilled') {
        setHealth(healthData.value)
      } else {
        setBackendError(healthData.reason?.message || 'Failed to connect to backend')
      }

      if (liveStateData.status === 'fulfilled') {
        setBlenderState(liveStateData.value)
      } else {
        setBlenderState({
          blender_available: false,
          character_name: 'Human',
          source: 'unavailable',
          timestamp_utc: new Date().toISOString(),
          error_details: liveStateData.reason?.message || 'Connection failed',
        })
      }
    } catch (err: any) {
      setBackendError(err?.message || 'Unexpected status check error')
    } finally {
      setIsCheckingBlender(false)
    }
  }, [])

  // Load audit logs
  const loadLogs = useCallback(async (caseId?: string) => {
    setIsLoadingLogs(true)
    try {
      const logData = await api.getLogs(25, caseId)
      setLogs(logData)
    } catch {
      // silently handle log loading error so it doesn't break primary UI
    } finally {
      setIsLoadingLogs(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    refreshStatus()
    loadLogs(currentCaseId)
  }, [refreshStatus, loadLogs, currentCaseId])

  // Single-button 1-click Generate & Apply workflow
  const handleGenerateAndApply = async (params: {
    text: string
    caseId: string
    characterName: string
    parserMode?: 'rule_based' | 'ai'
  }) => {
    // Duplicate submission guard
    if (isExecutingWorkflow) return

    setIsExecutingWorkflow(true)
    setLoadingStage('refining')
    setPreviewNetworkError(null)
    setPreview(null)
    setApplyResult(null)
    setCurrentCaseId(params.caseId)

    try {
      // Step A: Request live-state refinement preview via Ollama AI
      const refineResponse = await api.postRefine({
        text: params.text,
        case_id: params.caseId || null,
        character_name: 'Human',
        use_live_state: true, // Always live state for Generate & Apply
        parser_mode: params.parserMode || 'ai',
      })
      setPreview(refineResponse)

      // Step B: If rejected, STOP immediately
      if (refineResponse.status !== 'PREVIEW_READY') {
        return
      }

      const previewLogId = refineResponse.log_id
      if (!previewLogId) {
        throw new Error('Preview succeeded but server did not return a valid log_id.')
      }

      // Step C: Automatically call POST /apply using server-generated preview ID
      setLoadingStage('applying')
      const applyResponse = await api.postApply({
        preview_log_id: previewLogId,
        case_id: params.caseId || null,
        character_name: 'Human',
        confirm_apply: true,
      })
      setApplyResult(applyResponse)

      // Step D: Refresh live Blender state if mutation succeeded
      if (applyResponse.status === 'APPLIED' && applyResponse.verified) {
        refreshStatus()
      }
    } catch (err: any) {
      setPreviewNetworkError(
        err?.message || 'An unexpected error occurred during refinement and apply workflow.'
      )
    } finally {
      setIsExecutingWorkflow(false)
      setLoadingStage(null)
      loadLogs(params.caseId || undefined)
    }
  }

  // Optional Preview-Only simulation (preserves dry-run preview capability)
  const handlePreviewOnly = async (params: {
    text: string
    caseId: string
    characterName: string
    useLiveState: boolean
    parserMode?: 'rule_based' | 'ai'
  }) => {
    if (isExecutingWorkflow) return

    setIsExecutingWorkflow(true)
    setLoadingStage('refining')
    setPreviewNetworkError(null)
    setPreview(null)
    setApplyResult(null)
    setCurrentCaseId(params.caseId)

    try {
      const response = await api.postRefine({
        text: params.text,
        case_id: params.caseId || null,
        character_name: params.characterName || 'Human',
        use_live_state: params.useLiveState,
        parser_mode: params.parserMode,
      })
      setPreview(response)
    } catch (err: any) {
      setPreviewNetworkError(
        err?.message || 'An unexpected error occurred during refinement simulation.'
      )
    } finally {
      setIsExecutingWorkflow(false)
      setLoadingStage(null)
      loadLogs(params.caseId || undefined)
    }
  }

  // Forensic pencil sketch rendering workflow
  const handleRenderSketch = async (params?: { caseId?: string; characterName?: string }) => {
    if (isRenderingSketch) return

    setIsRenderingSketch(true)
    setSketchError(null)

    const targetCaseId = params?.caseId || currentCaseId
    const targetCharacter = params?.characterName || 'Human'

    try {
      const result = await api.postRenderSketch({
        case_id: targetCaseId,
        character_name: targetCharacter,
      })
      setSketchResult(result)
      if (result.status !== 'SUCCESS') {
        setSketchError(result.message || 'Forensic sketch generation failed.')
      }
    } catch (err: any) {
      setSketchError(
        err?.message || 'Network error encountered during sketch render request.'
      )
    } finally {
      setIsRenderingSketch(false)
    }
  }

  return (
    <div className="app-container">
      <Header
        health={health}
        blenderState={blenderState}
        isCheckingBlender={isCheckingBlender}
        backendError={backendError}
        onRefreshStatus={refreshStatus}
      />

      <main className="app-main">
        {/* Workspace Grid: Form on Left, Result Panel on Right */}
        <div className="workspace-grid">
          <section className="workspace-column">
            <RefinementForm
              onGenerateAndApply={handleGenerateAndApply}
              onPreviewOnly={handlePreviewOnly}
              onRefine={handleGenerateAndApply}
              onRenderSketch={handleRenderSketch}
              isRenderingSketch={isRenderingSketch}
              isLoading={isExecutingWorkflow}
              loadingStage={loadingStage}
              blenderState={blenderState}
              health={health}
            />
          </section>

          <section className="workspace-column">
            <PreviewPanel
              preview={preview}
              applyResult={applyResult}
              isLoading={isExecutingWorkflow}
              loadingStage={loadingStage}
              networkError={previewNetworkError}
              sketchResult={sketchResult}
              isRenderingSketch={isRenderingSketch}
              sketchError={sketchError}
              onRenderSketch={handleRenderSketch}
            />
          </section>
        </div>

        {/* Audit History Section */}
        <section className="audit-section">
          <AuditHistory
            logs={logs}
            isLoading={isLoadingLogs}
            onRefresh={(caseId) => loadLogs(caseId)}
            currentCaseId={currentCaseId}
          />
        </section>
      </main>

      <footer className="app-footer">
        <p>
          CrimeSketchAI &bull; Forensic Facial Sketch Composite Refinement &bull;{' '}
          <strong>Live Blender Bridge</strong> (Subject: Human)
        </p>
      </footer>
    </div>
  )
}

export default App
