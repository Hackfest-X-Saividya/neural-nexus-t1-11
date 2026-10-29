import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AuditHistory } from '../components/AuditHistory'
import type { AuditLogEntry } from '../types/api'

describe('AuditHistory Component', () => {
  const mockLogs: AuditLogEntry[] = [
    {
      id: 1,
      timestamp_utc: '2026-10-28T12:00:00Z',
      request_text: 'Make the nose slightly wider.',
      case_id: 'CASE-001',
      mode: 'dry_run',
      status: 'PREVIEW_READY',
      parsed_feature: 'nose width',
      target_identifier: 'nose:nose-scale-horiz-decr-incr:unsided',
      current_value: 0.2,
      proposed_delta: 0.05,
      proposed_value: 0.25,
      details_json: JSON.stringify({
        value_source: 'cached_reference',
        is_live_blender_value: false,
      }),
    },
    {
      id: 2,
      timestamp_utc: '2026-10-28T12:05:00Z',
      request_text: 'Make the suspect look angry.',
      case_id: 'CASE-002',
      mode: 'dry_run',
      status: 'REJECTED',
      error_message: 'Unsupported facial expression command.',
    },
  ]

  it('renders log records with status badges and details', () => {
    const mockRefresh = vi.fn()
    render(
      <AuditHistory
        logs={mockLogs}
        isLoading={false}
        onRefresh={mockRefresh}
        currentCaseId="CASE-001"
      />
    )

    expect(screen.getByText('Forensic Audit Trail')).toBeInTheDocument()
    expect(screen.getByText('CASE-001')).toBeInTheDocument()
    expect(screen.getByText('CASE-002')).toBeInTheDocument()
    expect(screen.getByText('PREVIEW_READY')).toBeInTheDocument()
    expect(screen.getByText('REJECTED')).toBeInTheDocument()
    expect(screen.getByText(/Make the nose slightly wider/i)).toBeInTheDocument()
  })

  it('filters by case ID when filter is submitted', () => {
    const mockRefresh = vi.fn()
    render(
      <AuditHistory
        logs={mockLogs}
        isLoading={false}
        onRefresh={mockRefresh}
        currentCaseId=""
      />
    )

    const filterInput = screen.getByPlaceholderText(/Filter by Case ID.../i)
    fireEvent.change(filterInput, { target: { value: 'CASE-001' } })

    const filterBtn = screen.getByRole('button', { name: 'Filter' })
    fireEvent.click(filterBtn)

    expect(mockRefresh).toHaveBeenCalledWith('CASE-001')
  })

  it('expands detail accordion when clicking inspect button', () => {
    const mockRefresh = vi.fn()
    render(
      <AuditHistory
        logs={mockLogs}
        isLoading={false}
        onRefresh={mockRefresh}
        currentCaseId=""
      />
    )

    const inspectBtns = screen.getAllByRole('button', { name: 'Inspect' })
    fireEvent.click(inspectBtns[0])

    expect(
      screen.getByText('nose:nose-scale-horiz-decr-incr:unsided')
    ).toBeInTheDocument()
  })
})

