import axios from 'axios'
import { generateMockReports } from './mockData'

// ---------------------------------------------------------------------------
// SWITCH THIS FLAG WHEN THE BACKEND (Person 5's FastAPI) IS READY.
// Everything else in the app calls the functions below — nothing in your
// components needs to change when you flip this.
// ---------------------------------------------------------------------------
const USE_MOCK = false
// Empty base = same origin; Vite proxies /reports and /stats to FastAPI in dev.
// For a deployed backend, set e.g. 'https://your-api.example.com'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const httpClient = axios.create({ baseURL: API_BASE_URL, timeout: 15000 })

// Cache mock reports so the "live" feel is consistent across a session
let MOCK_CACHE = null
function getMockReports() {
  if (!MOCK_CACHE) MOCK_CACHE = generateMockReports(150)
  return MOCK_CACHE
}

/**
 * Fetch reports, optionally filtered.
 * filters: { eventTypes: string[], states: string[], verificationStatus: string,
 *            dateFrom: string, dateTo: string, search: string }
 */
export async function fetchReports(filters = {}) {
  if (USE_MOCK) {
    let data = getMockReports()

    if (filters.eventTypes?.length) {
      data = data.filter((r) => filters.eventTypes.includes(r.event_type))
    }
    if (filters.states?.length) {
      data = data.filter((r) => filters.states.includes(r.state))
    }
    if (filters.verificationStatus && filters.verificationStatus !== 'all') {
      data = data.filter((r) => r.verification_status === filters.verificationStatus)
    }
    if (filters.dateFrom) {
      data = data.filter((r) => new Date(r.timestamp) >= new Date(filters.dateFrom))
    }
    if (filters.dateTo) {
      data = data.filter((r) => new Date(r.timestamp) <= new Date(filters.dateTo))
    }
    if (filters.search) {
      const q = filters.search.toLowerCase()
      data = data.filter(
        (r) => r.city.toLowerCase().includes(q) || r.text.toLowerCase().includes(q),
      )
    }
    return data
  }

  // REAL BACKEND CALL — matches Person 5's planned FastAPI endpoint:
  // GET /reports?event_type=...&state=...&status=...&date_from=...&date_to=...&q=...
  const { data } = await httpClient.get('/reports', {
    params: {
      event_type: filters.eventTypes?.length ? filters.eventTypes.join(',') : undefined,
      state: filters.states?.length ? filters.states.join(',') : undefined,
      status:
        filters.verificationStatus && filters.verificationStatus !== 'all'
          ? filters.verificationStatus
          : undefined,
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      q: filters.search || undefined,
    },
  })
  return data
}

/** Update a report's verification status — now represents a human ADMIN
 * OVERRIDE of the ML model's original call, not the primary verification
 * mechanism. Tags the change with verified_by: 'admin' so the audit trail
 * (and the Admin Panel UI) can distinguish ML-assessed reports from ones a
 * person has actually reviewed. */
export async function updateReportStatus(reportId, newStatus) {
  if (USE_MOCK) {
    const data = getMockReports()
    const report = data.find((r) => r.id === reportId)
    if (report) {
      report.verification_status = newStatus
      report.verified_by = 'admin'
    }
    return report
  }

  const { data } = await httpClient.patch(`/reports/${reportId}`, {
    verification_status: newStatus,
    verified_by: 'admin',
  })
  return data
}

/** Aggregated stats for the top ticker / stat cards */
export async function fetchStats() {
  if (USE_MOCK) {
    const data = getMockReports()
    const verified = data.filter((r) => r.verification_status === 'verified').length
    const critical = data.filter(
      (r) => ['flooding', 'thunderstorm'].includes(r.event_type) && r.credibility_score > 60,
    ).length
    const byState = {}
    data.forEach((r) => {
      byState[r.state] = (byState[r.state] || 0) + 1
    })
    const topState = Object.entries(byState).sort((a, b) => b[1] - a[1])[0]

    return {
      total: data.length,
      verifiedPct: Math.round((verified / data.length) * 100),
      activeAlerts: critical,
      mostAffectedState: topState ? topState[0] : '—',
    }
  }

  const { data } = await httpClient.get('/stats')
  return data
}

export async function fetchEvents() {
  if (USE_MOCK) {
    return []
  }
  const { data } = await httpClient.get('/events')
  return data
}

export async function fetchModelStatus() {
  if (USE_MOCK) {
    return {
      label_count: 0,
      last_refresh_at: null,
      message: 'Mock mode — no active learning status',
    }
  }
  const { data } = await httpClient.get('/model-status')
  return data
}

/** Subscribe to SSE live report/cluster counts. Returns an unsubscribe fn. */
export function subscribeLiveStats(onMessage) {
  if (USE_MOCK || typeof EventSource === 'undefined') {
    return () => {}
  }
  const base = API_BASE_URL || ''
  const es = new EventSource(`${base}/stream/stats`)
  es.onmessage = (evt) => {
    try {
      onMessage(JSON.parse(evt.data))
    } catch {
      /* ignore malformed */
    }
  }
  return () => es.close()
}

export async function createCitizenReport(payload) {
  if (USE_MOCK) {
    const data = getMockReports()
    const row = {
      id: `CIT-${Date.now()}`,
      text: payload.text,
      source: 'citizen_report',
      event_type: payload.event_type || 'rainfall',
      city: payload.city,
      state: 'Unknown',
      locality: null,
      lat: 19.07,
      lng: 72.87,
      timestamp: new Date().toISOString(),
      credibility_score: 50,
      verification_status: 'pending',
      verified_by: 'ml',
      media_url: payload.media_url || null,
      duplicate_group_id: null,
      hashtags: [],
      credibility_reasons: [],
    }
    data.unshift(row)
    return row
  }
  const { data } = await httpClient.post('/reports', payload)
  return data
}
