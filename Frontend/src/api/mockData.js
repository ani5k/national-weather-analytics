// Mock data shaped EXACTLY like what Person 5's backend API should return.
// This is the shared schema the whole team agreed on:
// { id, text, source, event_type, city, state, lat, lng, timestamp,
//   credibility_score, verification_status, media_url, duplicate_group_id }

export const CITIES = [
  {
    city: 'Mumbai',
    state: 'Maharashtra',
    lat: 19.076,
    lng: 72.8777,
    trafficScore: 92,
    affectedAreas: [
      { name: 'Dharavi', severity: 'high' },
      { name: 'Kurla', severity: 'high' },
      { name: 'Andheri West', severity: 'moderate' },
      { name: 'Bandra Kurla Complex', severity: 'low' },
    ],
  },
  {
    city: 'Chennai',
    state: 'Tamil Nadu',
    lat: 13.0827,
    lng: 80.2707,
    trafficScore: 81,
    affectedAreas: [
      { name: 'Velachery', severity: 'high' },
      { name: 'Mylapore', severity: 'moderate' },
      { name: 'T. Nagar', severity: 'low' },
    ],
  },
  {
    city: 'Kolkata',
    state: 'West Bengal',
    lat: 22.5726,
    lng: 88.3639,
    trafficScore: 74,
    affectedAreas: [
      { name: 'Salt Lake', severity: 'moderate' },
      { name: 'Howrah', severity: 'high' },
      { name: 'Behala', severity: 'moderate' },
    ],
  },
  {
    city: 'Bengaluru',
    state: 'Karnataka',
    lat: 12.9716,
    lng: 77.5946,
    trafficScore: 88,
    affectedAreas: [
      { name: 'Bellandur', severity: 'high' },
      { name: 'Koramangala', severity: 'moderate' },
      { name: 'Whitefield', severity: 'low' },
    ],
  },
  {
    city: 'Delhi',
    state: 'Delhi',
    lat: 28.6139,
    lng: 77.209,
    trafficScore: 95,
    affectedAreas: [
      { name: 'Minto Road', severity: 'high' },
      { name: 'Yamuna Bank', severity: 'high' },
      { name: 'Dwarka', severity: 'low' },
    ],
  },
  {
    city: 'Jaipur',
    state: 'Rajasthan',
    lat: 26.9124,
    lng: 75.7873,
    trafficScore: 58,
    affectedAreas: [
      { name: 'Malviya Nagar', severity: 'moderate' },
      { name: 'Sanganer', severity: 'low' },
    ],
  },
  {
    city: 'Guwahati',
    state: 'Assam',
    lat: 26.1445,
    lng: 91.7362,
    trafficScore: 66,
    affectedAreas: [
      { name: 'Anil Nagar', severity: 'high' },
      { name: 'Zoo Road', severity: 'moderate' },
    ],
  },
  {
    city: 'Bhubaneswar',
    state: 'Odisha',
    lat: 20.2961,
    lng: 85.8245,
    trafficScore: 52,
    affectedAreas: [
      { name: 'Old Town', severity: 'moderate' },
      { name: 'Patia', severity: 'low' },
    ],
  },
  {
    city: 'Lucknow',
    state: 'Uttar Pradesh',
    lat: 26.8467,
    lng: 80.9462,
    trafficScore: 69,
    affectedAreas: [
      { name: 'Gomti Nagar', severity: 'moderate' },
      { name: 'Chowk', severity: 'high' },
    ],
  },
  {
    city: 'Ahmedabad',
    state: 'Gujarat',
    lat: 23.0225,
    lng: 72.5714,
    trafficScore: 63,
    affectedAreas: [
      { name: 'Vastrapur', severity: 'low' },
      { name: 'Maninagar', severity: 'moderate' },
    ],
  },
]

// Approximate centroids for major states — used to draw density zones on the map.
// Kept as plain English-labelled points rather than full polygon boundaries (see
// MapView.jsx notes on why), so this list is safe to extend by hand any time.
export const STATE_CENTROIDS = [
  { state: 'Maharashtra', lat: 19.75, lng: 75.71 },
  { state: 'Tamil Nadu', lat: 11.13, lng: 78.66 },
  { state: 'West Bengal', lat: 22.99, lng: 87.86 },
  { state: 'Karnataka', lat: 15.32, lng: 75.71 },
  { state: 'Delhi', lat: 28.7, lng: 77.1 },
  { state: 'Rajasthan', lat: 27.02, lng: 74.22 },
  { state: 'Assam', lat: 26.2, lng: 92.94 },
  { state: 'Odisha', lat: 20.95, lng: 85.1 },
  { state: 'Uttar Pradesh', lat: 26.85, lng: 80.91 },
  { state: 'Gujarat', lat: 22.26, lng: 71.19 },
]

const EVENT_TYPES = [
  { key: 'rainfall', label: 'Rainfall', color: '#2563EB' },
  { key: 'thunderstorm', label: 'Thunderstorm', color: '#7C3AED' },
  { key: 'flooding', label: 'Flooding', color: '#EA580C' },
  { key: 'heatwave', label: 'Heatwave', color: '#B45309' },
  { key: 'fog', label: 'Fog', color: '#64748B' },
  { key: 'dust_storm', label: 'Dust Storm', color: '#A16207' },
  { key: 'strong_wind', label: 'Strong Wind', color: '#059669' },
]

const SOURCES = ['twitter', 'citizen_report', 'reddit', 'news_rss']
const STATUSES = ['verified', 'pending', 'rejected']

const SAMPLE_TEXT = {
  rainfall: 'Heavy rainfall reported since morning, waterlogging on main road.',
  thunderstorm: 'Loud thunderstorm with lightning strikes near the residential area.',
  flooding: 'Flood water entering ground-floor homes, residents evacuating.',
  heatwave: 'Extreme heat today, temperatures feel much higher than forecast.',
  fog: 'Dense fog since early morning, visibility very low on the highway.',
  dust_storm: 'Sudden dust storm reduced visibility, strong winds carrying dust.',
  strong_wind: 'Very strong winds uprooted trees near the market area.',
}

function randomFrom(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function jitter(value, amount) {
  return value + (Math.random() - 0.5) * amount
}

export function generateMockReports(count = 150) {
  const now = Date.now()
  const reports = []

  for (let i = 0; i < count; i++) {
    const place = randomFrom(CITIES)
    const eventType = randomFrom(EVENT_TYPES)
    const status = randomFrom(STATUSES)
    const hoursAgo = Math.random() * 72 // spread over the last 3 days

    // ~70% of reports have locality data, simulating a real pipeline where
    // not every source (e.g. a plain news RSS mention) includes it —
    // CityDetailModal is built to degrade gracefully when it's missing.
    const hasLocality = Math.random() < 0.7
    const locality = hasLocality ? randomFrom(place.affectedAreas).name : null

    reports.push({
      id: `RPT-${1000 + i}`,
      text: SAMPLE_TEXT[eventType.key],
      source: randomFrom(SOURCES),
      event_type: eventType.key,
      city: place.city,
      state: place.state,
      locality,
      lat: jitter(place.lat, 0.3),
      lng: jitter(place.lng, 0.3),
      timestamp: new Date(now - hoursAgo * 3600 * 1000).toISOString(),
      credibility_score: Math.floor(Math.random() * 100),
      verification_status: status,
      // Tracks whether the ML pipeline or a human admin set the current
      // status — most reports are ML-assessed; a handful simulate an
      // admin override, matching how the real system will work.
      verified_by: Math.random() < 0.12 ? 'admin' : 'ml',
      media_url: Math.random() > 0.5 ? 'placeholder.jpg' : null,
      duplicate_group_id: Math.random() > 0.8 ? `GRP-${Math.floor(i / 4)}` : null,
    })
  }

  return reports.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
}

export const EVENT_TYPE_META = EVENT_TYPES
