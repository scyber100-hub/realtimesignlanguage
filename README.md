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

GitHub 푸시
- 리포지토리를 초기화하고 푸시하려면(예시):
  1) `git init && git add . && git commit -m "init: kor→ksl realtime scaffold"`
  2) `git remote add origin https://github.com/scyber100-hub/realtimesignlanguage.git`
  3) `git push -u origin HEAD`
  - 토큰/권한 필요 시 GitHub PAT를 사용하세요.
