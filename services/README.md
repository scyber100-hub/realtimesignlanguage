서비스 개요와 API 스펙(초안)

asr-gateway (스트리밍 ASR 프록시)
- 입력: PCM 16k/16bit mono chunk (WS/gRPC)
- 출력(WS):
  {
    "id": "utt-123",
    "ts": 1699999999,
    "text": "안녕하세요 한…",
    "is_final": false,
    "confidence": 0.78
  }

text2gloss (HTTP/WS)
- POST /convert { text }
- 응답: { gloss: ["HELLO","KOREA"], conf: [0.9, 0.8] }

gloss2timeline (HTTP/WS)
- POST /compile { gloss: ["HELLO", ...], conf: [0.9,...] }
- 응답: SignTimeline(JSON). schemas/sign_timeline.schema.json 참고.

mixer (FFmpeg 기반)
- 입력: 원본 영상(영상+오디오) + Unity 인셋 영상(알파 또는 초록)
- 출력: RTMP/LL-HLS. 지연 최적화를 위해 파이프/저버퍼 설정 사용.

avatar-adapter (Unity 프로젝트 내)
- 입력: SignTimeline(JSON) (WS/UDP/파일워치 중 택1)
- 동작: clip id를 애니메이션 클립에 매핑, t_ms/ dur_ms대로 시퀀싱 재생

pipeline-server (본 리포지토리 포함)
- FastAPI + WebSocket
- 엔드포인트:
  - GET /healthz → 상태 확인
  - POST /ingest_text { text, start_ms?, gap_ms?, id? } → SignTimeline 생성 및 WS 브로드캐스트
  - WS /ws/timeline → 타임라인 push 수신
  - WS /ws/ingest → {type:"partial"|"final", session_id, text, start_ms?, gap_ms?} 증분 인입
    - 서버는 최초 full `timeline`, 이후 차이점부터 `timeline.replace`(from_t_ms 포함) 전송
