Config Presets

Endpoints (API key required)
- GET `/config/presets` → list available presets `{ name, mtime, size }`
- POST `/config/preset/save` { name, note? } → snapshot current config
- POST `/config/preset/load` { name } → apply preset to live settings

CLI Helper
- Requires server running at `http://127.0.0.1:8000`
- List: `.\.venv\Scripts\python.exe scripts\presets_cli.py list --api-key YOUR_KEY`
- Save: `.\.venv\Scripts\python.exe scripts\presets_cli.py save mypreset --api-key YOUR_KEY`
- Load: `.\.venv\Scripts\python.exe scripts\presets_cli.py load mypreset --api-key YOUR_KEY`

Preset Fields
- include_aux_channels, max_ingest_rps
- latency_p90_warn_ms, replace_ratio_warn, rate_limit_ratio_warn
- replace_min_events, replace_min_ms, replace_min_interval_ms

Storage
- Files are saved under `configs/presets/NAME.json` on the server.

