import { useMemo, useState } from 'react'
import { TrendingUp, TrendingDown, ChevronRight } from 'lucide-react'
import Modal from './Modal'
import EventBreakdownChart from './EventBreakdownChart'
import TimelineChart from './TimelineChart'
import { EVENT_TYPE_META } from '../api/mockData'

export default function AnalyticsHeadline({ reports }) {
  const [open, setOpen] = useState(false)

  const headline = useMemo(() => {
    if (reports.length === 0) return null

    const now = Date.now()
    const last24h = reports.filter((r) => now - new Date(r.timestamp) < 24 * 3600 * 1000)
    const prev24h = reports.filter((r) => {
      const age = now - new Date(r.timestamp)
      return age >= 24 * 3600 * 1000 && age < 48 * 3600 * 1000
    })

    // Find whichever event type moved the most, in either direction
    let leadType = null
    let leadPct = 0
    let leadDirection = 'up'

    EVENT_TYPE_META.forEach((et) => {
      const curr = last24h.filter((r) => r.event_type === et.key).length
      const prev = prev24h.filter((r) => r.event_type === et.key).length
      if (prev === 0 && curr === 0) return
      const pct = prev === 0 ? 100 : Math.round(((curr - prev) / prev) * 100)
      if (Math.abs(pct) >= Math.abs(leadPct)) {
        leadPct = pct
        leadType = et.label
        leadDirection = pct >= 0 ? 'up' : 'down'
      }
    })

    if (!leadType) return null
    return { leadType, leadPct: Math.abs(leadPct), leadDirection }
  }, [reports])

  if (!headline) return null

  const Icon = headline.leadDirection === 'up' ? TrendingUp : TrendingDown
  const colorClass = headline.leadDirection === 'up' ? 'text-alert' : 'text-verified'

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-between gap-3 bg-panel border border-storm rounded-lg px-4 py-3 text-left hover:bg-panel-raised transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-md flex items-center justify-center bg-void ${colorClass}`}>
            <Icon size={16} />
          </div>
          <p className="text-sm text-text-primary">
            <strong className="capitalize">{headline.leadType}</strong> reports have gone{' '}
            {headline.leadDirection === 'up' ? 'up' : 'down'}{' '}
            <strong className={colorClass}>{headline.leadPct}%</strong> compared to the previous 24
            hours.{' '}
            <span className="text-text-muted font-normal">Click to view full analytics.</span>
          </p>
        </div>
        <ChevronRight size={18} className="text-text-muted shrink-0" />
      </button>

      {open && (
        <Modal
          title="Analytics"
          subtitle="Event breakdown and report volume across the current filtered dataset"
          onClose={() => setOpen(false)}
          wide
        >
          <div className="flex flex-col gap-4">
            <EventBreakdownChart reports={reports} />
            <TimelineChart reports={reports} />
          </div>
        </Modal>
      )}
    </>
  )
}
