Prometheus Alerting (examples)

Key metrics
- ingest_to_broadcast_ms: histogram of ingest→broadcast latency
- timeline_broadcast_errors_total: broadcast errors (WebSocket send failures)
- ingest_messages_total: count of ingest messages (partial/final)
- websocket_clients: current WS clients (gauge)
- sessions_purged_total: sessions purged by TTL

Recording rules (example)
- groups:
  - name: realtime-sign
    rules:
    - record: job:ingest_broadcast_p90_ms
      expr: histogram_quantile(0.90, sum(rate(ingest_to_broadcast_ms_bucket[5m])) by (le)) * 1
    - record: job:ingest_broadcast_p99_ms
      expr: histogram_quantile(0.99, sum(rate(ingest_to_broadcast_ms_bucket[5m])) by (le)) * 1

Alerts (example)
- groups:
  - name: realtime-sign-alerts
    rules:
    - alert: HighIngestBroadcastLatencyP90
      expr: job:ingest_broadcast_p90_ms > 1200
      for: 5m
      labels: { severity: warning }
      annotations:
        summary: "High ingest→broadcast latency (p90 > 1200ms)"
    - alert: BroadcastErrors
      expr: increase(timeline_broadcast_errors_total[5m]) > 0
      for: 1m
      labels: { severity: warning }
      annotations:
        summary: "WebSocket broadcast errors occurred"
    - alert: RateLimitedExcess
      expr: increase(ingest_messages_total{type="partial"}[5m]) > 0 and increase(ingest_rate_limited_total[5m]) / increase(ingest_messages_total{type="partial"}[5m]) > 0.1
      for: 5m
      labels: { severity: warning }
      annotations:
        summary: "More than 10% of ingest messages were rate-limited"

