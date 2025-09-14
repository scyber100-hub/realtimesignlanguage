from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'services' / 'pipeline_server.py'
s = p.read_text(encoding='utf-8', errors='ignore')
lines = s.splitlines()
hits = []
for i, l in enumerate(lines, 1):
    if ('WhisperStreamer' in l) or ('transcribe_pcm16le' in l) or ('faster_whisper' in l) or ('from faster_whisper' in l):
        hits.append(i)

if not hits:
    print('no hits')
else:
    for h in hits:
        a, b = max(1, h-8), min(len(lines), h+12)
        print(f"--- around line {h} ---")
        for j in range(a, b+1):
            print(f"{j:4}: {lines[j-1]}")
