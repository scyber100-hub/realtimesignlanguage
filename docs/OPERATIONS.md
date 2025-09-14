Operations Guide

Overview
- This pipeline converts KOR text/audio to KSL glosses and a SignTimeline for a 3D avatar.
- It exposes HTTP + WebSocket endpoints and a web dashboard for real-time monitoring.

Run
- Create venv and install deps: see README.md
- Start server: `powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1`
- Open dashboard: http://localhost:8000/ (redirects to `/dashboard.html`)

Key Endpoints
- Health: GET `/healthz`
- Dashboard assets: `/dashboard.html`, `/app.css`, `/presets.js`
- Stats stream: WS `/ws/timeline` (pushes `stats` and `timeline` messages)
- Config: GET `/config`, POST `/config/update`
- Presets: GET `/config/presets`, POST `/config/preset/save`, `/config/preset/load`

Tuning Workflow
1) Open the dashboard. Watch latency histogram, latency p90 sparkline, replace ratio sparkline.
2) Set thresholds under “Update thresholds” (latency p90 warn, replace ratio, rate-limit ratio).
3) Adjust ingestion rate limit (`max_ingest_rps`) and include_aux_channels as needed.
4) Save the current tuning as a preset (name it per environment, e.g., `dev_fast`, `prod_balanced`).
5) For audio ingestion, test Whisper or Vosk bridges (see `docs/ASR_QUICKSTART.md`).

Caching
- Static files are served with `Cache-Control: public, max-age=STATIC_MAX_AGE_S` (default 3600s).
- Dynamic JSON endpoints (`/config`, `/stats`, `/events`, `/sessions`, `/healthz`) are served with `Cache-Control: no-store`.
  - Adjust via `STATIC_MAX_AGE_S` env var if needed.

Unity Integration
- Use WS `/ws/timeline` directly, or optionally enable UDP mirroring via `UNITY_UDP_ADDR=host:port`.
- Map gloss `clip` identifiers to Animator states using `TimelineAnimator`.
- Load mapping presets with `TimelineMappingLoader` and `unity/mappings/example_mappings.json`.

Operations Tips
- Keep `scripts/stop_demo.ps1` handy to terminate lingering demo/server processes.
- Use presets to quickly switch between dev/prod tuning.
- Monitor replace ratio. High ratio indicates frequent timeline corrections; adjust `replace_min_*` thresholds.

