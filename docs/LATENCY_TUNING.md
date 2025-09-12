1초 지연 목표 튜닝 체크리스트

ASR
- 윈도우 160–320ms, 중첩 50% 내 → 부분 결과 즉시 방출
- VAD pre-roll 50–120ms, trailing 80–150ms로 보수적으로
- 문장부호 지연 최소화: 온디바이스 lightweight punctuation 예측기 사용

NLP/합성
- 규칙/사전 로드 메모리 상주, I/O 없음
- 증분(diff) 처리: 이전 글로스와 비교해 델타만 타임라인 갱신

전달/아바타
- WS/UDP로 타임라인 롤링 윈도우(0.4–0.8s) 선행 전송
- 프리페치 큐(2–4 이벤트) 유지, 정정 이벤트는 미래 구간만 교체

FFmpeg 송출
- veryfast/zerolatency, B프레임 제거, 짧은 GOP(키프레임 0.5–1s)
- 오디오/비디오 동기 버퍼 최소화, `-fflags nobuffer`

네트워크
- 동일 AZ/로컬 네트워크 배치, NIC/RTT 최적화

