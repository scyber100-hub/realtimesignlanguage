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
  - GET /metrics → Prometheus 지표 노출
  - GET /stats → 경량 런타임 통계(JSON)
  - GET /config → 안전 설정 조회(version, include_aux_channels, max_ingest_rps, enable_metrics)
  - POST /config/update { include_aux_channels?, max_ingest_rps? }
  - POST /ingest_text { text, start_ms?, gap_ms?, id? } → SignTimeline 생성 및 WS 브로드캐스트
  - POST /text2gloss { text } → { gloss, conf }
  - POST /gloss2timeline { gloss[], conf?[], start_ms?, gap_ms? } → SignTimeline(JSON)
  - POST /lexicon/update { items: { "한국": "KOREA", ... } } → 런타임 사전 갱신
  - POST /lexicon/upload (multipart/form-data) file=@ko_domain_lexicon.json → 런타임 사전 업로드
  - POST /lexicon/snapshot { note? } → 현재 오버레이 사전을 lexicon/versions/overlay-*.json로 저장
  - GET /lexicon/versions → 저장된 스냅샷 목록(name, mtime, size)
  - POST /lexicon/rollback { name } → 지정 스냅샷으로 롤백 적용
  - GET /timeline/last → 마지막 브로드캐스트 타임라인 페이로드(JSON)
  - GET /events/recent?n=100 → 최근 타임라인 이벤트 요약 목록(count/items)
  - WS /ws/timeline → 타임라인 push 수신
  - WS /ws/ingest → {type:"partial"|"final", session_id, text, start_ms?, gap_ms?} 증분 인입
    - 서버는 최초 full `timeline`, 이후 차이점부터 `timeline.replace`(from_t_ms 포함) 전송
    - `origin_ts`(ms) 필드를 포함하면 ingest→broadcast 지연 히스토그램에 반영

추가 참고
- GET /sessions_full → last_update_ms 포함 세션 상세 목록
- 환경 변수 SESSION_TTL_S(기본 600초) 설정 시 마지막 업데이트 이후 유휴 세션 자동 정리
보안/설정
- API 키(선택): `API_KEY` 설정 시 /ingest_text, /lexicon/update, /ws/ingest 보호
- CORS_ALLOW_ORIGINS, LOG_LEVEL, ENABLE_METRICS 등은 README 참고
