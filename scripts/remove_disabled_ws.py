from pathlib import Path

p = Path(__file__).resolve().parents[1] / "services" / "pipeline_server.py"
text = p.read_text(encoding="utf-8", errors="ignore")

start_marker = '@app.websocket("/ws/ingest_disabled")'
end_marker = '@app.on_event("startup")'

start = text.find(start_marker)
if start != -1:
    end = text.find(end_marker, start)
    if end == -1:
        end = len(text)
    new_text = text[:start] + text[end:]
    p.write_text(new_text, encoding="utf-8")
    print("Removed disabled /ws/ingest block.")
else:
    print("Disabled block not found. Nothing to remove.")

