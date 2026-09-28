import { useState, useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Marker } from 'react-leaflet'
import L from 'leaflet'
import CityDetailModal from './CityDetailModal'

// India's bounding box — keeps the map from panning off into grey nothingness
// or duplicate "world copies".
const INDIA_BOUNDS = [
  [6.0, 67.0],
  [37.5, 98.5],
]

// City fill = orange, outline = deep indigo, per your spec.
const CITY_FILL = '#F97316'
const CITY_STROKE = '#3730A3'

function makeLabelIcon(text) {
  return L.divIcon({
    className: 'state-label',
    html: text,
    iconSize: [0, 0],
  })
}

export default function MapView({ reports, searchQuery }) {
  const [selectedCity, setSelectedCity] = useState(null)

  // IMPORTANT: city hotspots are derived entirely from the `reports` prop —
  // never from a hardcoded list. This is what makes the map automatically
  // reflect real data the moment the backend goes live: no separate "city
  // dataset" needs to exist anywhere. A city's position is the average
  // lat/lng of its reports; its "traffic" is just its report count relative
  // to the busiest city currently in view.
  const cityHotspots = useMemo(() => {
    const groups = {}
    reports.forEach((r) => {
      if (!groups[r.city]) {
        groups[r.city] = { city: r.city, state: r.state, latSum: 0, lngSum: 0, count: 0 }
      }
      const g = groups[r.city]
      g.latSum += r.lat
      g.lngSum += r.lng
      g.count += 1
    })

    const list = Object.values(groups).map((g) => ({
      city: g.city,
      state: g.state,
      lat: g.latSum / g.count,
      lng: g.lngSum / g.count,
      count: g.count,
    }))

    const maxCount = Math.max(1, ...list.map((c) => c.count))
    return list.map((c) => ({ ...c, trafficScore: Math.round((c.count / maxCount) * 100) }))
  }, [reports])

  const visibleCities = useMemo(() => {
    const q = (searchQuery || '').trim().toLowerCase()
    if (!q) return cityHotspots
    return cityHotspots.filter(
      (c) => c.city.toLowerCase().includes(q) || c.state.toLowerCase().includes(q),
    )
  }, [cityHotspots, searchQuery])

  return (
    <div className="rounded-lg overflow-hidden border border-storm shadow-glow h-[560px] relative bg-void">
      <MapContainer
        center={[22.9, 79.1]}
        zoom={4.6}
        zoomSnap={0.5}
        zoomDelta={0.5}
        minZoom={4.3}
        maxZoom={9}
        scrollWheelZoom={true}
        maxBounds={INDIA_BOUNDS}
        maxBoundsViscosity={1.0}
        worldCopyJump={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        />

        {visibleCities.map((c) => (
          <CircleMarker
            key={c.city}
            center={[c.lat, c.lng]}
            radius={12 + (c.trafficScore / 100) * 10}
            pathOptions={{
              color: CITY_STROKE,
              weight: 3,
              fillColor: CITY_FILL,
              fillOpacity: 0.95,
            }}
            eventHandlers={{ click: () => setSelectedCity(c) }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{c.city}</p>
                <p className="text-xs text-gray-500">
                  {c.count} reports · click marker to view city layout
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {visibleCities.map((c) => (
          <Marker
            key={`label-${c.city}`}
            position={[c.lat, c.lng]}
            icon={makeLabelIcon(c.city)}
            interactive={false}
          />
        ))}
      </MapContainer>

      <div className="absolute bottom-3 left-3 z-[400] bg-void/95 border border-storm rounded-md px-3 py-2 flex items-center gap-1.5 text-[11px] text-text-muted shadow-glow">
        <span
          className="w-2.5 h-2.5 rounded-full border-2"
          style={{ backgroundColor: CITY_FILL, borderColor: CITY_STROKE }}
        />
        High-traffic city — click to view event details
      </div>

      {selectedCity && (
        <CityDetailModal
          city={selectedCity}
          reports={reports.filter((r) => r.city === selectedCity.city)}
          onClose={() => setSelectedCity(null)}
        />
      )}
    </div>
  )
}
