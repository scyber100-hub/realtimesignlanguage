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

