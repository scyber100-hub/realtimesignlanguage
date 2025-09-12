AI 기반 실시간 방송 수어 통번역 플랫폼 (KOR→KSL)

목표
- 방향: 한국어 → 한국수어(KSL)
- 출력: 3D 아바타 인셋(방송 송출용)
- 지연: E2E 1초 목표(공격적으로 튜닝)
- 채널: 방송 송출(RTMP/LL-HLS), 추후 WebRTC 뷰어 병행 가능

구성 요약
- Ingest: 방송 입력(RTMP/SRT) → 오디오 분리(FFmpeg) → 스트리밍 ASR로 전송
- ASR: 한국어 스트리밍 음성 인식(부분 결과/중간 수정)
- NLP: 텍스트 정규화 → KSL 글로스 변환(규칙+사전, 이후 NMT)
- 합성: 글로스 → 아바타 모션 클립 타임라인(JSON) → Unity에서 재생
- 패키징: Unity 인셋(알파/녹색배경) → FFmpeg 믹싱 → RTMP/LL-HLS 송출

이 리포지토리에서 제공하는 것
- 아키텍처와 인터페이스(서비스 경계, 메시지 스키마)
- 간단한 텍스트→글로스→타임라인 Python 데모(로컬 실행 가능)
- FFmpeg 인입/송출 예시 커맨드, 운영 팁(지연 최적화)
- Unity 연동 가이드(타임라인 JSON → 클립 재생 규약)

빠른 시작
1) Python 3.10+ 준비
2) 데모 실행(텍스트→타임라인 JSON):
   - 명령: `python scripts/demo_text_to_sign.py --text "안녕하세요 한국 날씨" --out out/timeline.json`
   - 결과: `out/timeline.json` 생성 → Unity 어댑터에서 소비

실행형 파이프라인 서버(WS 브로드캐스트)
- 설치: `pip install -r requirements.txt`
- 서버 실행: `powershell -ExecutionPolicy Bypass -File scripts/run_server.ps1`
- 타임라인 수신(WS): `python scripts/example_ws_client.py`
- 텍스트 인입(모의 ASR): `powershell -ExecutionPolicy Bypass -File scripts/ingest_text.ps1 -Text "속보 태풍 오늘 한국"`
  - 클라이언트 콘솔에 SignTimeline JSON이 브로드캐스트됩니다.

증분 스트리밍(모의 ASR)
- WS 인입: `python scripts/mock_asr_stream.py --text "안녕하세요 오늘 한국 날씨 속보 태풍"`
- 서버는 최초 `timeline`, 이후 `timeline.replace(from_t_ms)` 메시지를 브로드캐스트합니다.

오프라인 ASR(Vosk, 선택)
- 준비: `pip install vosk` 후 한국어 모델 다운로드(예: `vosk-model-small-ko-0.22`) 후 경로 지정
- 실행: `python scripts/vosk_ingest_from_rtmp.py --model <vosk_model_dir> --rtmp rtmp://origin/live/stream`
- 동작: FFmpeg로 오디오 추출→Vosk 실시간 인식→/ws/ingest로 partial/final 전송

오프라인/온프레 ASR(Whisper, 선택)
- 준비: `pip install faster-whisper` 및 FFmpeg 설치
- 실행: `python scripts/whisper_ingest_from_rtmp.py --model base --rtmp rtmp://origin/live/stream`
- 동작: FFmpeg 오디오→chunk 단위 Whisper 추론→partial 전송(간단 스트리밍)

폴더 구조
- `services/` 서비스 경계 문서 및 스텁
- `packages/` 규칙/타임라인 생성 라이브러리(파이썬)
- `schemas/` 메시지/타임라인 스키마(JSON Schema)
- `scripts/` 로컬 데모/유틸리티
- `docs/` 운영/튜닝/Unity 연동 문서

다음 단계(제안)
- 스트리밍 ASR 선택 및 통합(Riva/Vosk/Whisper-Streaming 중 택1)
- Unity 아바타 프로젝트에 타임라인 JSON 소비 어댑터(WS/UDP/파일) 구현
- RTMP 송출 파이프라인(FFmpeg 컴포지터) 구성 → 파일럿 방송

운영 문서
- `ARCHITECTURE.md` 전체 구조 및 서비스 경계
- `docs/FFMPEG_PIPELINES.md` 인입/송출 예시와 저지연 팁
- `docs/LATENCY_TUNING.md` 1초 지연 튜닝 체크리스트
- `docs/UNITY_ADAPTER.md` Unity 연동 규약
 - `unity/` Unity용 C# 스크립트와 사용법
 - `docs/UNITY_CHANNELS.md` 채널(손/얼굴/시선) 블렌딩 가이드

API 요약(서버 포함)
- `GET /healthz` 상태 확인
- `GET /metrics` Prometheus 지표
- `POST /text2gloss { text }` → `{ gloss, conf }`
- `POST /gloss2timeline { gloss[], conf?[], start_ms?, gap_ms? }` → SignTimeline(JSON)
- `POST /ingest_text { text, start_ms?, gap_ms?, id? }` → WS 브로드캐스트 포함
- `WS /ws/ingest` 증분 인입(`partial`/`final`) → `timeline`/`timeline.replace` 브로드캐스트
- `WS /ws/timeline` 타임라인 구독

보안/설정(환경 변수)
- `API_KEY`: 설정 시 `POST /ingest_text`, `POST /lexicon/update`, `WS /ws/ingest?key=...` 에서 키 필요
- `CORS_ALLOW_ORIGINS`: `*,https://your.host` 형태로 허용 오리진 지정(기본 `*`)
- `DEFAULT_START_MS`/`DEFAULT_GAP_MS`: 기본 타임라인 시작/간격(ms)
- `LOG_LEVEL`: INFO/DEBUG 등 로그 레벨
- `ENABLE_METRICS`: `1`(기본)/`0`

도메인 사전(핫 리로드)
- `POST /lexicon/update { items: { "한국": "KOREA", ... } }`
- 런타임 오버레이 사전으로 즉시 반영(프로세스 내 메모리)

Docker 실행
- 로컬 빌드/실행: `powershell -ExecutionPolicy Bypass -File scripts/run_docker.ps1`
- 또는: `docker compose up --build`

Self-check
- 빠른 점검: `python scripts/self_check.py`

웹 대시보드
- 서버 기동 후 브라우저에서 `http://localhost:8000/` 접속
- 실시간 WebSocket 타임라인을 콘솔로 확인하고 `POST /ingest_text` 테스트 가능

환경설정(.env)
- 예시: `.env.example`를 `.env`로 복사 후 값 설정 → 서버가 자동 로드

GitHub 푸시
- 리포지토리를 초기화하고 푸시하려면(예시):
  1) `git init && git add . && git commit -m "init: kor→ksl realtime scaffold"`
  2) `git remote add origin https://github.com/scyber100-hub/realtimesignlanguage.git`
  3) `git push -u origin HEAD`
  - 토큰/권한 필요 시 GitHub PAT를 사용하세요.
