# SIH Architecture & Accuracy Note (one-pager)

## Architecture (two planes)

```
┌─────────────────────────────────────────────────────────────┐
│  STREAMING INGEST PLANE                                     │
│  Open-Meteo · News RSS · Reddit · IMD bulletins · Citizen   │
│           ↓ publish_raw()                                   │
│  Redpanda topic: weather.raw  →  worker enrich              │
│  (Mongo poll fallback if broker down on Windows demos)      │
└───────────────────────────┬─────────────────────────────────┘
                            ↓ enriched docs
┌─────────────────────────────────────────────────────────────┐
│  MONGO SERVE PLANE                                          │
│  weather_db.weather_data + admin_labels                     │
│  FastAPI: /reports /events /stats /stream/stats (SSE)       │
│  React dashboard · Events clusters · Admin why-score        │
└─────────────────────────────────────────────────────────────┘
```

## Trust fusion (rubric `trust_fusion_v3`)
Explainable 0–100 score from weighted factors: location, media, timestamp, source reputation, detail, weather metrics, `#IMD`, corroboration, official bulletin anchor, geo–time plausibility, text–image heuristics, media forensics lite (EXIF/reuse/visual). Admin UI expands **Why this score** with +/- points.

## Official anchors
IMD-tier RSS bulletins (`pipeline/collect_imd.py`) labeled `is_official_anchor`; citizen/social reports attach `official_anchor_id` in enrichment.

## Multilingual + media
Multilingual MiniLM embeddings when installed (hash fallback otherwise). EN+HI seed pairs demo shared clusters. Media forensics are **heuristics** (reuse / EXIF / consistency) — not production deepfake detection.

## Active learning + impact
Admin verify/reject writes `admin_labels`; `ml/refresh_prototypes.py` refreshes prototypes + held-out metric banner. Event popups show approximate people-at-risk / hospitals / roads (demo estimates, not NDMA figures).

## Honest limits
Not a full X firehose or Spark lakehouse; streaming story works with Redpanda when available and Mongo/SSE otherwise.
