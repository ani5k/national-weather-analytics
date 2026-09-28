import { EVENT_TYPE_META } from '../api/mockData'

const STATUS_STYLE = {
  verified: 'bg-verified/10 text-verified',
  pending: 'bg-warn/10 text-warn',
  rejected: 'bg-alert/10 text-alert',
}

const SOURCE_LABEL = {
  'open-meteo': 'Open-Meteo',
  news_rss: 'News',
  reddit: 'Reddit',
  citizen_report: 'Citizen',
  imd: 'IMD',
  twitter: 'Twitter',
}

function timeAgo(timestamp) {
  const mins = Math.floor((Date.now() - new Date(timestamp)) / 60000)
  if (Number.isNaN(mins)) return '—'
  if (mins < 0) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function mixedPreview(reports, perSource = 8) {
  const buckets = new Map()
  for (const report of reports) {
    const key = report.source || 'other'
    if (!buckets.has(key)) buckets.set(key, [])
    const bucket = buckets.get(key)
    if (bucket.length < perSource) bucket.push(report)
  }
  const lists = [...buckets.values()]
  const mixed = []
  const depth = Math.max(0, ...lists.map((list) => list.length))
  for (let i = 0; i < depth; i += 1) {
    for (const list of lists) {
      if (list[i]) mixed.push(list[i])
    }
  }
  return mixed
}

export default function ReportFeed({ reports }) {
  const colorByType = Object.fromEntries(EVENT_TYPE_META.map((e) => [e.key, e.color]))
  const visible = mixedPreview(reports)

  return (
    <div className="bg-panel border border-storm rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Reports from Accumulated Data</h3>
        <span className="text-[11px] text-text-muted font-mono">{reports.length} total</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-[360px] overflow-y-auto pr-1">
        {visible.map((r) => (
          <div key={r.id} className="border border-storm rounded-md p-2.5 bg-void">
            <div className="flex items-center justify-between mb-1">
              <span
                className="text-[11px] font-medium capitalize px-1.5 py-0.5 rounded"
                style={{ backgroundColor: `${colorByType[r.event_type]}1A`, color: colorByType[r.event_type] }}
              >
                {r.event_type.replace('_', ' ')}
              </span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${STATUS_STYLE[r.verification_status]}`}>
                {r.verification_status}
              </span>
            </div>
            <p className="text-xs text-text-primary line-clamp-2">{r.text}</p>
            <div className="flex items-center justify-between mt-1.5 text-[10px] text-text-muted font-mono">
              <span>{r.city}, {r.state} · {SOURCE_LABEL[r.source] || r.source}</span>
              <span>{timeAgo(r.timestamp)}</span>
            </div>
          </div>
        ))}
        {reports.length === 0 && (
          <p className="text-xs text-text-muted text-center mt-8 col-span-full">
            No reports match the current filters.
          </p>
        )}
      </div>
    </div>
  )
}
