import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { EVENT_TYPE_META } from '../api/mockData'

export default function EventBreakdownChart({ reports }) {
  const counts = EVENT_TYPE_META.map((et) => ({
    name: et.label,
    key: et.key,
    count: reports.filter((r) => r.event_type === et.key).length,
    color: et.color,
  }))

  return (
    <div className="bg-panel border border-storm rounded-lg p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">Reports by Event Type</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={counts} layout="vertical" margin={{ left: 10 }}>
          <XAxis type="number" stroke="oklch(50% 0.02 236.824)" fontSize={11} />
          <YAxis
            dataKey="name"
            type="category"
            stroke="oklch(50% 0.02 236.824)"
            fontSize={11}
            width={90}
          />
          <Tooltip
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid oklch(83% 0.03 236.824)',
              borderRadius: 8,
            }}
            labelStyle={{ color: 'oklch(27% 0.03 236.824)' }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {counts.map((c) => (
              <Cell key={c.key} fill={c.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
