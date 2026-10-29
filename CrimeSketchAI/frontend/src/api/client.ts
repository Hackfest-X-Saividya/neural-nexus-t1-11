/**
 * API client for CrimeSketchAI backend.
 * Configurable base URL, robust error handling, and type-safe endpoints.
 */

import type {
  HealthResponse,
  FeatureInfo,
  LiveStateResponse,
  RefinementRequest,
  RefinementResponse,
  RefinementApplyRequest,
  RefinementApplyResponse,
  AuditLogEntry,
  SketchRenderRequest,
  SketchRenderResponse,
} from '../types/api'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

class ApiError extends Error {
  status?: number
  details?: unknown

  constructor(message: string, status?: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    })

    if (!response.ok) {
      let errorBody: any = null
      try {
        errorBody = await response.json()
      } catch {
        // Response is not JSON
      }
      const message =
        errorBody?.detail ||
        errorBody?.message ||
        `HTTP Error ${response.status}: ${response.statusText}`
      throw new ApiError(message, response.status, errorBody)
    }

    return (await response.json()) as T
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err
    }
    // Network error or connection refused
    throw new ApiError(
      `Network connection failed when reaching backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`,
      0,
      err
    )
  }
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health')
  },

  async getFeatures(): Promise<FeatureInfo[]> {
    return request<FeatureInfo[]>('/features')
  },

  async getLiveState(characterName = 'Human'): Promise<LiveStateResponse> {
    const params = new URLSearchParams({ character_name: characterName })
    return request<LiveStateResponse>(`/state?${params.toString()}`)
  },

  async postRefine(req: RefinementRequest): Promise<RefinementResponse> {
    return request<RefinementResponse>('/refine', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  async postApply(req: RefinementApplyRequest): Promise<RefinementApplyResponse> {
    return request<RefinementApplyResponse>('/apply', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  async getLogs(limit = 25, caseId?: string): Promise<AuditLogEntry[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (caseId && caseId.trim()) {
      params.append('case_id', caseId.trim())
    }
    return request<AuditLogEntry[]>(`/logs?${params.toString()}`)
  },

  async postRenderSketch(req: SketchRenderRequest = {}): Promise<SketchRenderResponse> {
    return request<SketchRenderResponse>('/render-sketch', {
      method: 'POST',
      body: JSON.stringify({
        character_name: req.character_name || 'Human',
        case_id: req.case_id || null,
      }),
    })
  },
}

