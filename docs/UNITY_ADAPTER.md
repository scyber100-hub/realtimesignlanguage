Unity 아바타 연동 가이드(초안)

목표
- SignTimeline(JSON) 메시지를 받아 3D 아바타 애니메이션 클립을 시간축에 맞춰 재생.

메시지
- schemas/sign_timeline.schema.json 참조.
- 예시:
  {
    "id": "signtimeline-...",
    "created_ms": 1700000000000,
    "events": [
      {"t_ms":0,   "clip":"HELLO",   "dur_ms":620, "channel":"default"},
      {"t_ms":680, "clip":"KOREA",   "dur_ms":700},
      {"t_ms":1440,"clip":"WEATHER", "dur_ms":680}
    ]
  }

재생 규약(권장)
- 타임라인 기준: 수신 시점을 t=0으로 오프셋 적용(또는 created_ms 기준 동기화)
- clip id → Animator/Timeline 트랙에 매핑
- 겹침 이벤트는 우선순위/채널별 블렌딩으로 처리
- 부분 업데이트: 동일 id의 수정 메시지 수신 시 t>=now+Δ 구간만 교체

네트워킹(옵션)
- WebSocket 서버에서 timeline push 또는 Unity가 poll
- 파일 워치: JSON 파일 갱신 감지 후 로드(프로토타입 쉬움)

렌더링/송출 팁
- 알파 채널 있는 영상 출력(ProRes 4444 등) 또는 녹색 배경 키잉
- 카메라/조명 고정, 손가락/표정 디테일 강조, 인셋 16:9 → 9:16 변형 고려

