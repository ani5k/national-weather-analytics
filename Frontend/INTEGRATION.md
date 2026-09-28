# Integration Guide — Frontend ↔ Backend/Data Pipeline

This is the exact contract the frontend expects. If your API/data matches this
shape precisely, integration should be a one-line change (see "Going live" at
the bottom). Field name mismatches (e.g. `eventType` vs `event_type`) are the
most common integration bug — copy these names exactly.

## 1. The Report object

Every report — regardless of source (Twitter/X, Reddit, RSS, citizen
submission) — must be shaped like this by the time it reaches the frontend:

```json
{
  "id": "RPT-1000",
  "text": "Heavy rainfall reported since morning, waterlogging on main road.",
  "source": "citizen_report",
  "event_type": "flooding",
  "city": "Mumbai",
  "state": "Maharashtra",
  "locality": "Dharavi",
  "lat": 19.076,
  "lng": 72.8777,
  "timestamp": "2026-09-05T09:12:00.000Z",
  "credibility_score": 82,
  "verification_status": "verified",
  "verified_by": "ml",
  "media_url": null,
  "duplicate_group_id": null
}
```

**Field notes:**

| Field | Type | Required? | Notes |
|---|---|---|---|
| `id` | string | Yes | Any unique string |
| `text` | string | Yes | The report's raw or cleaned text |
| `source` | string | Yes | `"twitter"` \| `"citizen_report"` \| `"reddit"` \| `"news_rss"` |
| `event_type` | string | Yes | One of: `rainfall`, `thunderstorm`, `flooding`, `heatwave`, `fog`, `dust_storm`, `strong_wind` — this is the ML classifier's output |
| `city` | string | Yes | Used to group reports for the map hotspots — **spelling must be consistent** across reports (e.g. always "Bengaluru", not sometimes "Bangalore") or the same city will incorrectly split into two hotspots |
| `state` | string | Yes | Used for the "Most Affected" stat |
| `locality` | string or `null` | **No — optional but recommended** | Neighbourhood/ward name. If your citizen-report form or geocoding step can capture this, the "Affected Areas" feature in the city drill-down becomes fully functional. If omitted, that section just shows a note instead of breaking |
| `lat` / `lng` | number | Yes | Real coordinates — city hotspot position is literally the average of these across a city's reports, so bad coordinates visibly break the map |
| `timestamp` | string | Yes | ISO 8601 format exactly like the example — used for date filtering and the volume chart |
| `credibility_score` | number 0–100 | Yes | Output of the fake/duplicate-detection model |
| `verification_status` | string | Yes | `"verified"` \| `"pending"` \| `"rejected"` — **this is what the ML model sets automatically now** |
| `verified_by` | string | Yes | `"ml"` or `"admin"` — set to `"ml"` whenever your model sets the status; the frontend sets this to `"admin"` automatically when a human uses the Admin Panel to override it. This is what lets the Admin Panel show which reports were machine-decided vs. human-reviewed |
| `media_url` | string or `null` | No | Photo/video URL when available |
| `duplicate_group_id` | string or `null` | No | Dedup / event cluster id |
| `hashtags` | string[] | No | e.g. `["#IMD","#Rainfall"]` |
| `credibility_reasons` | string[] | No | Explainable trust reasons for Admin |
| `risk_severity` | string or `null` | No | `low` \| `moderate` \| `high` |

### Extra endpoints (v2)

- `POST /reports` — citizen submission body `{ text, city, state?, locality?, lat?, lng?, event_type?, media_url?, hashtags? }`
- `GET /events` — corroboration clusters for the Events map/view
- `POST /enrich` — batch NLP/dedup/trust enrichment

## 2. The ML verification workflow — what actually changed

Nothing in the frontend needs to change for this. The Admin Panel's
Verify/Pending/Reject buttons still exist — they now represent a **human
override of the ML's decision**, not the primary verification method. Here's
the intended flow:

1. A new report comes in → your ingestion pipeline runs it through the event
   classifier and the fake/credibility model
2. The model writes `verification_status` and `credibility_score` directly,
   and sets `verified_by: "ml"`
3. The frontend displays it immediately with that ML-assigned status — no
   admin action required for it to show up correctly
4. If an admin manually changes the status via the Admin Panel, the frontend
   sends `verified_by: "admin"` in that request — your `PATCH` endpoint should
   just store whatever `verified_by` value it receives, not recompute it

**One thing your team needs to agree on together, not something I can decide
for you**: what counts as an "Active Alert" for the stats panel. Right now in
mock mode it's "flooding or thunderstorm reports with credibility over 60" —
that's a placeholder. Decide on a real threshold (e.g. "Critical-risk reports
in the last 24 hours") and either compute it in `/stats` on the backend, or
tell the frontend dev the exact rule so it can be computed client-side.

## 3. Required endpoints

### `GET /reports`
Returns an array of Report objects (shape above). Accepts these optional
query parameters — if a parameter is absent, don't filter on it:

```
GET /reports?event_type=flooding,rainfall&state=Maharashtra&status=verified&date_from=2026-09-01&date_to=2026-09-05&q=mumbai
```

| Param | Meaning |
|---|---|
| `event_type` | Comma-separated list of event types to include |
| `state` | Comma-separated list of states to include |
| `status` | Single verification status to filter to |
| `date_from` / `date_to` | ISO date strings, inclusive range |
| `q` | Free-text search — should match against `city` and `text` at minimum |

### `GET /stats`
Returns pre-aggregated numbers so the frontend isn't crunching thousands of
records client-side as your dataset grows:

```json
{
  "total": 4210,
  "verifiedPct": 61,
  "activeAlerts": 14,
  "mostAffectedState": "Assam"
}
```

### `PATCH /reports/{id}`
Body:
```json
{ "verification_status": "verified", "verified_by": "admin" }
```
Returns the updated Report object.

## 4. CORS — don't skip this

Whatever framework the backend uses (FastAPI, Express, etc.), it must
explicitly allow cross-origin requests from the frontend's origin, or every
request will be silently blocked by the browser with no useful error beyond
"Failed to fetch" in the console. Allow at minimum:
- `http://localhost:5173` (local dev)
- Whatever URL the frontend is deployed to later

## 5. Pagination — a decision to make before it becomes a fire drill

There is currently no pagination — `/reports` is expected to return
everything matching the filters in a single response. Fine for hundreds of
reports; not fine for tens of thousands. Decide now whether you'll add
`?page=1&limit=50`-style pagination, so it's not a last-minute rework.

## 6. Going live — the actual switch

Everything above is already fully implemented and tested against **mock
data that follows this exact schema** — so if your real API matches it,
integration is one change, in one file: `src/api/client.js`

```js
const USE_MOCK = false
const API_BASE_URL = 'https://your-deployed-backend-url.com'
```

That's it. No component files need to change. If something breaks after
flipping this flag, it almost always means a field name or type doesn't
match this document exactly — check that first before assuming it's a
deeper bug.
