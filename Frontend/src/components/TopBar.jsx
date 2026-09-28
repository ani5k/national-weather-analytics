import { CloudLightning, Database } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function TopBar({ view, setView }) {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-storm bg-void">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-rain/10 text-rain">
          <CloudLightning size={20} />
        </div>
        <div>
          <h1 className="font-display font-semibold text-lg leading-tight text-text-primary">
            Bharath Weather
          </h1>
          <p className="text-xs text-text-muted font-mono">A National Weather Analytics Dashboard</p>
        </div>
      </div>

      <nav className="flex items-center gap-1 bg-panel rounded-lg p-1 border border-storm">
        {[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'events', label: 'Events' },
          { id: 'admin', label: 'Admin Panel' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setView(tab.id)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              view === tab.id
                ? 'bg-rain text-white'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-text-muted text-xs font-mono">
          <Database size={13} />
          Data synced
        </div>
        <span className="text-sm font-mono text-text-muted">
          {now.toLocaleTimeString('en-IN')}
        </span>
      </div>
    </header>
  )
}
