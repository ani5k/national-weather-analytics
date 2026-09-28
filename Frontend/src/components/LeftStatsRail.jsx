export default function LeftStatsRail({ stats }) {
  if (!stats) {
    return <aside className="w-56 shrink-0 border-r border-storm" />
  }

  const blocks = [
    {
      label: 'Total Reports',
      value: stats.total,
      accent: 'border-rain',
      big: true,
    },
    {
      label: 'Most Affected',
      value: stats.mostAffectedState,
      accent: 'border-alert',
      big: true,
    },
    {
      label: 'Verified',
      value: `${stats.verifiedPct}%`,
      accent: 'border-verified',
      big: false,
    },
    {
      label: 'Active Alerts',
      value: stats.activeAlerts,
      accent: 'border-warn',
      big: false,
    },
  ]

  return (
    <aside className="w-56 shrink-0 border-r border-storm bg-void p-5 flex flex-col gap-6">
      {blocks.map((b) => (
        <div key={b.label} className={`border-l-4 ${b.accent} pl-3`}>
          <p className="text-[11px] uppercase tracking-wider text-text-muted font-mono mb-1">
            {b.label}
          </p>
          <p
            className={`font-display font-semibold text-text-primary leading-none ${
              b.big ? 'text-3xl' : 'text-xl'
            }`}
          >
            {b.value}
          </p>
        </div>
      ))}
    </aside>
  )
}
