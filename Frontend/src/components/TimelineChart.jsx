import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function TimelineChart({ reports }) {
  // Bucket reports into hourly counts for the last 24 hours
  const buckets = {}
  const now = new Date()
  for (let i = 23; i >= 0; i--) {
    const hourLabel = new Date(now - i * 3600 * 1000).getHours() + ':00'
    buckets[hourLabel] = 0
  }
  reports.forEach((r) => {
    const hourLabel = new Date(r.timestamp).getHours() + ':00'
    if (hourLabel in buckets) buckets[hourLabel] += 1
  })
  const data = Object.entries(buckets).map(([hour, count]) => ({ hour, count }))

  return (
    <div className="bg-panel border border-storm rounded-lg p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">Report Volume (Last 24h)</h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563EB" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="hour" stroke="oklch(50% 0.02 236.824)" fontSize={10} interval={3} />
          <YAxis stroke="oklch(50% 0.02 236.824)" fontSize={10} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid oklch(83% 0.03 236.824)',
              borderRadius: 8,
            }}
            labelStyle={{ color: 'oklch(27% 0.03 236.824)' }}
          />
          <Area type="monotone" dataKey="count" stroke="#2563EB" fill="url(#volumeFill)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
