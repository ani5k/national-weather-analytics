# National Weather Analytics Platform — Runbook

## Quick local demo (Windows)

1. Start Mongo (Docker):
   ```bash
   docker start weather-mongo
   # or: docker run -d --name weather-mongo -p 27017:27017 mongo:7
   ```

2. Ensure `.env` exists (copy from `.env.example`).

3. Seed volume + live sources:
   ```bash
   python seed_bulk_reports.py --count 520
   python run_pipeline.py
   python seed_multilingual_reports.py
   ```

4. API:
   ```bash
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

5. Optional worker (Kafka or Mongo-poll fallback):
   ```bash
   python -m worker.main
   ```

6. Frontend:
   ```bash
   cd Frontend
   npm install
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

7. Demo streaming tick + active learning refresh:
   ```bash
   python demo_streaming.py
   python ml/refresh_prototypes.py
   ```

Open http://127.0.0.1:5173 and http://127.0.0.1:8000/docs  
Live SSE: `/stream/stats` · Model banner: `/model-status`

## Full stack (Compose)

```bash
docker compose up --build
```

Kafka external port: `127.0.0.1:19092`  
Set `KAFKA_BOOTSTRAP=127.0.0.1:19092` for host-side collectors.

## Canonical scripts

| Script | Purpose |
|--------|---------|
| `run_pipeline.py` | Open-Meteo + RSS + IMD anchors + Reddit + enrich |
| `scheduled_validated.py` | Hourly loop of the same |
| `seed_bulk_reports.py` | 500+ demo reports |
| `seed_multilingual_reports.py` | EN+HI paired clusters + media forensics demo |
| `demo_streaming.py` | Publish one `weather.raw` / Mongo demo message |
| `ml/refresh_prototypes.py` | Active-learning prototype refresh + held-out metric |
| `worker/main.py` | Stream consumer / enricher |

See `docs/SIH_ARCHITECTURE.md` for ingest plane vs serve plane slide.

Legacy one-off collectors (`collector.py`, `scheduled_merged.py`, etc.) are superseded — prefer the scripts above.
