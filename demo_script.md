# Weather Data Pipeline – Demo Script

## 1. Pipeline Overview
- 3 data sources: OpenWeatherMap, Open-Meteo, 5-day Forecast
- MongoDB Atlas for storage
- Runs every hour automatically
- Deduplication, event categorization, data validation

## 2. Step 1: Show Running Collector
```bash
ps aux | grep scheduled_validated
