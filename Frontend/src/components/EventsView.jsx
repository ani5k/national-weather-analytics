import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'

const SEVERITY_COLOR = {
  high: '#EA580C',
  moderate: '#CA8A04',
  low: '#2563EB',
}

function clusterSummary(ev) {
  const n = ev.report_count ?? 0
  const k = ev.source_count ?? (ev.sources || []).length
  const m = ev.media_count ?? 0
  const trust = ev.trust_01 != null ? ev.trust_01 : ((ev.avg_credibility || 0) / 100).toFixed(2)
  return `${n} reports · ${k} sources · ${m} media · trust ${trust}`
}

export default function EventsView({ events }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg overflow-hidden border border-storm h-[420px] relative bg-void">
        <MapContainer
          center={[22.9, 79.1]}
          zoom={4.6}
          minZoom={4.3}
          maxZoom={9}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution="Tiles &copy; Esri"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          />
          {events.map((ev) => (
            <CircleMarker
              key={ev.id}
              center={[ev.lat, ev.lng]}
              radius={10 + Math.min(14, ev.report_count * 2)}
              pathOptions={{
                color: '#1e3a8a',
                weight: 2,
                fillColor: SEVERITY_COLOR[ev.risk_severity] || SEVERITY_COLOR.low,
                fillOpacity: 0.85,
              }}
            >
              <Popup>
                <div className="text-sm max-w-xs">
                  <p className="font-semibold capitalize">
                    {ev.event_type.replace('_', ' ')} · {ev.city}
                  </p>
                  <p className="text-xs text-gray-600">{clusterSummary(ev)}</p>
                  <p className="text-xs mt-1 text-gray-700">
                    Est. people at risk: ~{(ev.people_at_risk || 0).toLocaleString()} ·{' '}
                    {ev.risk_severity} severity
                  </p>
                  {(ev.hospitals_nearby > 0 || ev.major_roads_nearby > 0) && (
                    <p className="text-[10px] text-gray-500">
                      ~{ev.hospitals_nearby} hospitals · ~{ev.major_roads_nearby} major roads nearby
                      (approx.)
                    </p>
                  )}
                  {ev.official_anchor_id && (
                    <p className="text-[10px] text-blue-700 mt-1">
                      Anchored to IMD bulletin {ev.official_anchor_id}
                    </p>
                  )}
                  {!!ev.languages?.length && (
                    <p className="text-[10px] text-gray-500">langs: {ev.languages.join(', ')}</p>
                  )}
                  <p className="text-xs mt-1">{ev.sample_text}</p>
                  <p className="text-[10px] mt-1 text-gray-500">{(ev.sources || []).join(', ')}</p>
                  {!!ev.member_ids?.length && (
                    <p className="text-[10px] mt-1 text-gray-400 font-mono">
                      members: {ev.member_ids.slice(0, 4).join(', ')}
                      {ev.member_ids.length > 4 ? '…' : ''}
                    </p>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <div className="bg-panel border border-storm rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-3">Event clusters ({events.length})</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-[320px] overflow-y-auto">
          {events.map((ev) => (
            <div key={ev.id} className="border border-storm rounded-md p-3 bg-void">
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium capitalize">{ev.event_type.replace('_', ' ')}</span>
                <span className="font-mono text-text-muted">{ev.risk_severity}</span>
              </div>
              <p className="text-xs text-text-primary line-clamp-2">{ev.sample_text}</p>
              <p className="text-[10px] text-text-muted font-mono mt-1">
                {ev.city}, {ev.state} · {clusterSummary(ev)}
              </p>
              <p className="text-[10px] text-text-muted mt-0.5">
                Est. people at risk: ~{(ev.people_at_risk || 0).toLocaleString()}
              </p>
              {ev.official_anchor_id && (
                <p className="text-[10px] text-rain mt-0.5">
                  Anchored to IMD bulletin {ev.official_anchor_id}
                </p>
              )}
              {!!ev.languages?.length && (
                <p className="text-[10px] text-thunder mt-0.5">Languages: {ev.languages.join(', ')}</p>
              )}
              {!!ev.hashtags?.length && (
                <p className="text-[10px] text-rain mt-1">{ev.hashtags.slice(0, 4).join(' ')}</p>
              )}
              {!!ev.member_ids?.length && (
                <p className="text-[10px] text-text-muted font-mono mt-1">
                  → {ev.member_ids.length} member reports
                </p>
              )}
            </div>
          ))}
          {!events.length && (
            <p className="text-xs text-text-muted col-span-full text-center py-8">No event clusters yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
