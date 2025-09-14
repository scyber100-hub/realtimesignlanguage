Development Notes

Branch
- feat/dashboard-asr-integration (pushed to origin)

Scope Implemented
- ASR WS (/ws/asr) with Whisper streamer and language hint
- Dashboard (app.css, dashboard.html/js) with live stats, histograms/sparklines, tooltips, CSV download, pagination
- Presets API (list/save/load), CLI helper, docs
- Logs endpoints (JSON + CSV) and dashboard integration
- Sessions/events server-side pagination; session detail endpoint
- Static caching, GZip middleware; root redirect to /dashboard.html
- Unity mapping (TimelineAnimator CrossFade + channel→layer), MappingLoader, example mapping JSON
- Scripts: run_asr_demo, ffmpeg_loop, smoke/self-tests, helpers

Follow-ups / TODOs
- Server filter: /sessions_full?session_id= query support (front-end currently falls back to client-side filter)
- Dashboard: session detail mini timeline view; graph customization (window length/threshold/colours)
- Security/ops: headers tuning, Docker/compose polishing, monitoring hooks

Operational Notes
- Root path / redirects to /dashboard.html to avoid legacy encoding in index.html
- Dynamic API responses set Cache-Control: no-store; static files are cached with STATIC_MAX_AGE_S (default 3600)
- GZip enabled (ENABLE_GZIP=1)

