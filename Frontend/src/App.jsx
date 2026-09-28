import { useEffect, useState, useCallback } from 'react'
import TopBar from './components/TopBar'
import HeaderFilters from './components/HeaderFilters'
import LeftStatsRail from './components/LeftStatsRail'
import MapView from './components/MapView'
import AnalyticsHeadline from './components/AnalyticsHeadline'
import ReportFeed from './components/ReportFeed'
import AdminTable from './components/AdminTable'
import EventsView from './components/EventsView'
import CitizenReportForm from './components/CitizenReportForm'
import { fetchReports, fetchStats, fetchEvents, fetchModelStatus, subscribeLiveStats } from './api/client'

const DEFAULT_FILTERS = {
  eventTypes: [],
  states: [],
  verificationStatus: 'all',
  dateFrom: '',
  dateTo: '',
  search: '',
}

export default function App() {
  const [view, setView] = useState('dashboard')
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [reports, setReports] = useState([])
  const [events, setEvents] = useState([])
  const [stats, setStats] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [liveCounts, setLiveCounts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [reportData, statData, eventData, modelData] = await Promise.all([
        fetchReports(filters),
        fetchStats(),
        fetchEvents(),
        fetchModelStatus().catch(() => null),
      ])
      setReports(Array.isArray(reportData) ? reportData : [])
      setStats(statData)
      setEvents(Array.isArray(eventData) ? eventData : [])
      setModelStatus(modelData)
    } catch (err) {
      console.error('Failed to load dashboard data', err)
      setReports([])
      setStats(null)
      setEvents([])
      setError(err?.message || 'Could not reach the API. Is it running on port 8000?')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadData()
    const t = setInterval(loadData, 60000)
    return () => clearInterval(t)
  }, [loadData])

  useEffect(() => {
    const unsub = subscribeLiveStats((payload) => {
      if (payload?.total_reports != null) {
        setLiveCounts(payload)
        setStats((prev) =>
          prev
            ? { ...prev, total: payload.total_reports }
            : { total: payload.total_reports, verifiedPct: 0, activeAlerts: 0, mostAffectedState: '—' },
        )
      }
    })
    return unsub
  }, [])

  return (
    <div className="min-h-screen flex flex-col font-body bg-void">
      <TopBar view={view} setView={setView} />
      <HeaderFilters filters={filters} setFilters={setFilters} />

      <div className="flex flex-1 overflow-hidden">
        <LeftStatsRail stats={stats} />

        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
          {liveCounts && (
            <p className="text-[10px] font-mono text-text-muted">
              Live stream · reports {liveCounts.total_reports} · clusters {liveCounts.event_clusters}
            </p>
          )}
          {loading && <p className="text-xs text-text-muted font-mono">Loading reports...</p>}
          {error && (
            <div className="rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
              {error}{' '}
              <button type="button" className="underline font-medium" onClick={loadData}>
                Retry
              </button>
            </div>
          )}

          {view === 'dashboard' && (
            <>
              <CitizenReportForm onCreated={loadData} />
              <MapView reports={reports} searchQuery={filters.search} />
              <AnalyticsHeadline reports={reports} />
              <ReportFeed reports={reports} />
            </>
          )}
          {view === 'events' && <EventsView events={events} />}
          {view === 'admin' && (
            <AdminTable reports={reports} onUpdate={loadData} modelStatus={modelStatus} />
          )}
        </main>
      </div>
    </div>
  )
}
