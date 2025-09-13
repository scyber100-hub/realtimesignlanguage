# DEVLOG: Realtime KOR→KSL Pipeline – Progress Log

This log summarizes notable changes, decisions, and artifacts for ongoing development.

## Scope (Sep 2025)
- Stabilize server (FastAPI + WS) and add observable metrics/alerts
- Improve incremental replace quality to reduce noisy `timeline.replace`
- Add dashboard (public/) with runtime stats and alert visibility

## Changes

### Server
- API key guard definition placed before usage to avoid import issues
- Metrics: add `ingest_rate_limited_total (RATE_LIMITED)` counter
- Endpoints added
  - `GET /stats/alerts` – current alerts
  - `GET /stats/alerts/history?n=30` – recent alerts (server-side history)
  - `POST /stats/alerts/clear` – clear alerts history
- WS `/ws/ingest` now delegates to `_process_stream_in` (shared quality/rate checks)
- Replace quality tuning
  - Env: `REPLACE_MIN_EVENTS=2`, `REPLACE_MIN_MS=300`, `REPLACE_MIN_INTERVAL_MS=150`
  - Runtime update via `POST /config/update`
- Config exposure in `GET /config`: latency/replace thresholds and replace tuning values

### Dashboard (public/index.html)
- Alert badges (⚡ latency / ♻️ replace / 🚥 rate-limit) with color states
- Alerts panel
  - Fetch from `/stats/alerts/history` (count selectable)
  - Auto-refresh, type filter, Clear, Export JSON
- Replace tuning controls (min events / ms / min interval) with `/config/update`

### Docs & Env
- `.env.example` updated with alert thresholds, history size, replace tuning
- README updated with an “Updates” section for alerts/tuning/dashboard

## Validation
- `pip install -r requirements.txt`
- `python scripts/self_check.py` – PASS
- Manual dashboard smoke test against local server

## Open PR
- Branch: `fix/server-stability`
- PR: https://github.com/scyber100-hub/realtimesignlanguage/pull/2

## Next (Proposed)
See docs/ROADMAP.md – tracked as GitHub issues as well.

