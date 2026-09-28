import { Search, ChevronDown } from 'lucide-react'
import { EVENT_TYPE_META, CITIES } from '../api/mockData'

const STATES = [...new Set(CITIES.map((c) => c.state))].sort()

export default function HeaderFilters({ filters, setFilters }) {
  const toggleEventType = (key) => {
    setFilters((prev) => {
      const active = prev.eventTypes.includes(key)
      return {
        ...prev,
        eventTypes: active
          ? prev.eventTypes.filter((k) => k !== key)
          : [...prev.eventTypes, key],
      }
    })
  }

  const toggleState = (state) => {
    setFilters((prev) => {
      const states = prev.states || []
      const active = states.includes(state)
      return {
        ...prev,
        states: active ? states.filter((s) => s !== state) : [...states, state],
      }
    })
  }

  const eventLabel =
    filters.eventTypes.length === 0
      ? 'All event types'
      : filters.eventTypes.length === 1
        ? EVENT_TYPE_META.find((e) => e.key === filters.eventTypes[0])?.label
        : `${filters.eventTypes.length} event types`

  const stateLabel =
    !filters.states?.length
      ? 'All states'
      : filters.states.length === 1
        ? filters.states[0]
        : `${filters.states.length} states`

  return (
    <div className="flex flex-wrap items-center gap-2 px-6 py-3 bg-panel border-b border-storm">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search size={14} className="absolute left-2.5 top-2.5 text-text-muted" />
        <input
          type="text"
          placeholder="Search city or keyword..."
          value={filters.search}
          onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))}
          className="w-full bg-void border border-storm rounded-md pl-8 pr-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-rain"
        />
      </div>

      <details className="relative z-[1200] group">
        <summary className="list-none cursor-pointer flex items-center gap-1.5 bg-void border border-storm rounded-md px-3 py-1.5 text-sm text-text-primary hover:bg-panel-raised">
          {eventLabel}
          <ChevronDown size={14} className="text-text-muted" />
        </summary>
        <div className="absolute z-[1200] mt-1 w-56 bg-void border border-storm rounded-md shadow-glow p-2 flex flex-col gap-1 max-h-64 overflow-y-auto">
          {EVENT_TYPE_META.map((et) => (
            <label
              key={et.key}
              className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-panel cursor-pointer text-sm"
            >
              <input
                type="checkbox"
                checked={filters.eventTypes.includes(et.key)}
                onChange={() => toggleEventType(et.key)}
                className="accent-rain"
              />
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: et.color }} />
              {et.label}
            </label>
          ))}
        </div>
      </details>

      <details className="relative z-[1200] group">
        <summary className="list-none cursor-pointer flex items-center gap-1.5 bg-void border border-storm rounded-md px-3 py-1.5 text-sm text-text-primary hover:bg-panel-raised">
          {stateLabel}
          <ChevronDown size={14} className="text-text-muted" />
        </summary>
        <div className="absolute z-[1200] mt-1 w-56 bg-void border border-storm rounded-md shadow-glow p-2 flex flex-col gap-1 max-h-64 overflow-y-auto">
          {STATES.map((state) => (
            <label
              key={state}
              className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-panel cursor-pointer text-sm"
            >
              <input
                type="checkbox"
                checked={(filters.states || []).includes(state)}
                onChange={() => toggleState(state)}
                className="accent-rain"
              />
              {state}
            </label>
          ))}
        </div>
      </details>

      <details className="relative z-[1200] group">
        <summary className="list-none cursor-pointer flex items-center gap-1.5 bg-void border border-storm rounded-md px-3 py-1.5 text-sm text-text-primary capitalize hover:bg-panel-raised">
          {filters.verificationStatus === 'all' ? 'All statuses' : filters.verificationStatus}
          <ChevronDown size={14} className="text-text-muted" />
        </summary>
        <div className="absolute z-[1200] mt-1 w-40 bg-void border border-storm rounded-md shadow-glow p-1 flex flex-col">
          {['all', 'verified', 'pending', 'rejected'].map((status) => (
            <button
              key={status}
              onClick={(e) => {
                setFilters((p) => ({ ...p, verificationStatus: status }))
                e.target.closest('details').removeAttribute('open')
              }}
              className="text-left px-2 py-1.5 rounded hover:bg-panel text-sm capitalize text-text-primary"
            >
              {status === 'all' ? 'All statuses' : status}
            </button>
          ))}
        </div>
      </details>

      <details className="relative z-[1200] group">
        <summary className="list-none cursor-pointer flex items-center gap-1.5 bg-void border border-storm rounded-md px-3 py-1.5 text-sm text-text-primary hover:bg-panel-raised">
          Date range
          <ChevronDown size={14} className="text-text-muted" />
        </summary>
        <div className="absolute z-[1200] mt-1 w-56 bg-void border border-storm rounded-md shadow-glow p-3 flex flex-col gap-2">
          <label className="text-xs text-text-muted">From</label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => setFilters((p) => ({ ...p, dateFrom: e.target.value }))}
            className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm text-text-primary"
          />
          <label className="text-xs text-text-muted">To</label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => setFilters((p) => ({ ...p, dateTo: e.target.value }))}
            className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm text-text-primary"
          />
        </div>
      </details>

      <button
        onClick={() =>
          setFilters({
            eventTypes: [],
            states: [],
            verificationStatus: 'all',
            dateFrom: '',
            dateTo: '',
            search: '',
          })
        }
        className="text-xs text-text-muted hover:text-text-primary underline underline-offset-2 ml-1"
      >
        Reset
      </button>
    </div>
  )
}
