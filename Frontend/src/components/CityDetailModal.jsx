import { useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import Modal from './Modal'
import { EVENT_TYPE_META } from '../api/mockData'

const COLOR_BY_TYPE = Object.fromEntries(EVENT_TYPE_META.map((e) => [e.key, e.color]))

const SEVERITY_STYLE = {
  high: 'bg-alert/10 text-alert border-alert/30',
  moderate: 'bg-warn/10 text-warn border-warn/30',
  low: 'bg-verified/10 text-verified border-verified/30',
}

export default function CityDetailModal({ city, reports, onClose }) {
  // Affected areas are derived from an OPTIONAL `locality` field on each
  // report — not hardcoded. If your citizen-report form or scraping pipeline
  // doesn't capture locality yet, this section says so honestly instead of
  // showing fake area names.
  const affectedAreas = useMemo(() => {
    const withLocality = reports.filter((r) => r.locality)
    if (withLocality.length === 0) return []

    const counts = {}
    withLocality.forEach((r) => {
      counts[r.locality] = (counts[r.locality] || 0) + 1
    })

    return Object.entries(counts)
      .map(([name, count]) => {
        const share = count / withLocality.length
        const severity = share > 0.4 ? 'high' : share > 0.15 ? 'moderate' : 'low'
        return { name, count, severity }
      })
      .sort((a, b) => b.count - a.count)
  }, [reports])

  return (
    <Modal
      title={city.city}
      subtitle={`${city.state} · ${reports.length} reports · traffic index ${city.trafficScore}/100`}
      onClose={onClose}
      wide
    >
      <div className="rounded-md overflow-hidden border border-storm mb-4 h-[300px]">
        <MapContainer
          center={[city.lat, city.lng]}
          zoom={11}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          />
          <CircleMarker
            center={[city.lat, city.lng]}
            radius={9}
            pathOptions={{ color: '#3730A3', fillColor: '#F97316', fillOpacity: 0.9, weight: 2 }}
          >
            <Popup>{city.city} city centre</Popup>
          </CircleMarker>

          {reports.map((r) => {
            const color = COLOR_BY_TYPE[r.event_type] || '#2563EB'
            const isUnverified = r.verification_status !== 'verified'
            return (
              <CircleMarker
                key={r.id}
                center={[r.lat, r.lng]}
                radius={isUnverified ? 7 : 5}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.85,
                  weight: isUnverified ? 2 : 1,
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-semibold capitalize">{r.event_type.replace('_', ' ')}</p>
                    {r.locality && <p className="text-xs text-gray-500">{r.locality}</p>}
                    <p className="text-xs text-gray-500 mt-1">{r.text}</p>
                    <p className="text-xs mt-1 capitalize">
                      Status: <strong>{r.verification_status}</strong>
                    </p>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-4">
        {EVENT_TYPE_META.map((e) => (
          <div key={e.key} className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: e.color }} />
            {e.label}
          </div>
        ))}
      </div>

      <h3 className="text-sm font-semibold text-text-primary mb-2">Affected areas</h3>
      {affectedAreas.length > 0 ? (
        <div className="flex flex-col gap-2">
          {affectedAreas.map((area) => (
            <div
              key={area.name}
              className={`flex items-center justify-between px-3 py-2 rounded-md border text-sm ${SEVERITY_STYLE[area.severity]}`}
            >
              <span className="font-medium">{area.name}</span>
              <span className="text-xs uppercase tracking-wide font-mono">
                {area.count} reports · {area.severity} impact
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-text-muted italic">
          Locality-level detail isn't available for this city yet — reports need a
          <code className="mx-1 px-1 bg-panel rounded">locality</code>
          field for this section to populate.
        </p>
      )}
    </Modal>
  )
}
