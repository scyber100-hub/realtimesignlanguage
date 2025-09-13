Monitoring and Logs

Metrics
- Prometheus endpoint: `GET /metrics` (enable via `ENABLE_METRICS=1`)
- Key metrics:
  - `pipeline_request_latency_seconds` (endpoint label)
  - `timeline_broadcast_total`
  - `ingest_messages_total` (type label)

Timeline JSON logs
- Path: `logs/timeline.log`
- Format: one JSON per line
  - { ts, type, session_id, id, from_t_ms, event_count }
- Useful for reconstructing latency and replacement patterns.

Quick tips
- Tail logs: `Get-Content -Path logs/timeline.log -Wait` (PowerShell)
- Scrape metrics with Prometheus and visualize with Grafana.

# Monitoring / Dashboards

This project exposes Prometheus metrics at `/metrics`.

## Quick Start (Prometheus + Grafana)

1) Start pipeline (port 8000)
```
docker compose up -d pipeline
```

2) Start monitoring stack
```
docker compose -f docker-compose.monitoring.yml up -d
```

3) Access
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Import dashboard: `docs/grafana/pipeline_dashboard.json`

Prometheus config: `docs/prometheus.yml`
Alert rules: `docs/alerts/prometheus_rules.yml`

## Key Metrics
- `ingest_to_broadcast_ms` (Histogram): latency from ingest to timeline broadcast
- `ingest_messages_total{type=partial|final}` (Counter)
- `ingest_rate_limited_total` (Counter)
- `timeline_broadcast_total` (Counter)
- `websocket_clients` (Gauge)

## Example Alerts
- p90 latency > 1200 ms over 5m
- rate-limit ratio > 0.1 over 5m

See `docs/alerts/prometheus_rules.yml` for details.
