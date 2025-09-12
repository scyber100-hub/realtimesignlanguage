개요(1초 지연 목표 아키텍처)

경로
1) Ingest: 방송 입력(RTMP/SRT) → FFmpeg로 오디오 분리(48kHz/mono/16bit) → ASR로 스트리밍
2) ASR: 한국어 스트리밍 인식(부분 결과/중간 수정) → 문장 끝 힌트(VAD/문장부호 예측)
3) NLP: 텍스트 정규화 → 토크나이징/품사 → KSL 글로스 변환(규칙+사전) → 비수지 태깅(초기 규칙)
4) 합성: 글로스 시퀀스 → 모션 클립 타임라인 JSON(clip id, t, dur, channel)
5) 아바타: Unity에서 타임라인 수신/재생(알파 키/녹색 배경)
6) 송출: FFmpeg로 원본 영상에 인셋 PiP 합성 → RTMP/LL-HLS 송출

지연 예산(권장)
- Ingest+큐: 50–100ms
- ASR: 300–500ms(윈도우 160–320ms, 중첩 50%)
- NLP(글로스): 50–120ms
- 합성/전달: 80–150ms
- 인셋 합성/송출: 150–250ms
- 합계: ~0.8–1.2s (1초 목표권)

서비스 경계(초기)
- `asr-gateway` (gRPC/WebSocket): PCM 16k/16bit chunk in → partial transcript out
- `text2gloss` (HTTP/WS): text in → gloss[] + tags
- `gloss2timeline` (HTTP/WS): gloss[] in → SignTimeline(JSON)
- `avatar-adapter` (Unity): SignTimeline in → 클립 재생
- `mixer` (FFmpeg): 원본+인셋 합성 → RTMP out

메시지 스키마(요약)
- TranscriptPartial: { id, ts, text, is_final, confidence }
- GlossResult: { id, ts, gloss: ["HELLO","KOREA"], conf: [0.9,0.82] }
- SignTimeline v0: { id, created_ms, events: [{ t_ms, clip, dur_ms, channel }], meta }

실행 흐름(증분 처리)
1) ASR 부분 결과 수신 즉시 → incremental gloss 변환 (diff 기반)
2) 근미래(400–800ms) 타임라인을 rolling window로 미리 전송 → 아바타 프리페치
3) ASR 정정(edit) 시 타임라인 보정 이벤트 발행(replace window)
4) 신뢰도 낮을 때 fallback(인간 통역) 시그널 전송(하이브리드 대비)

확장 포인트
- 사전/도메인 템플릿(뉴스/기상/재난) → 정확도↑
- 표정/시선/강세 채널 분리 → 자연스러움↑
- LL-HLS 이중화 → 대규모 분산 배포

