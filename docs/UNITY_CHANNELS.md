Unity 채널 블렌딩 가이드(초안)

개요
- 타임라인 이벤트는 `channel` 필드를 포함(예: `default`, `hands`, `face`, `gaze`, `body`).
- 본 리포지토리 기본 컴파일러는 중요 이벤트(BREAKING/지진/태풍)에 대해 `face` 채널에 `FACE_ALERT`를 함께 배치.

권장 구성
- Animator 레이어 분리: Base(default) / Face(face) / Gaze(gaze) / UpperBody(hands)
- 레이어 가중치: Face/Gaze는 0.6–0.9 범위에서 블렌딩, 마스크로 해당 본만 영향
- 이벤트 동기화: 동일 `t_ms`인 다른 채널 이벤트는 동시에 트리거

실행 규칙
- default 채널: 메인 수어 동작(손/팔/몸통), 클립마다 루트모션/리타게팅 적용
- face 채널: 표정/입모양/강세, 클립 길이는 메인 이벤트 길이 내에서 제한
- gaze 채널: 시선 방향(좌/우/전방), 카메라 프레이밍과 충돌 주의

기본 맵핑(예시)
- BREAKING/EARTHQUAKE/TYPHOON → face: FACE_ALERT
- 이후 프로젝트에 맞게 `packages/sign_timeline/timeline.py`의 `_FACE_CLIPS`/채널 매핑 확장

테스트
- `scripts/mock_asr_stream.py`로 스트림, Unity에서 Animator 각 레이어 로그 확인
- 과도한 블렌딩으로 손가락/얼굴이 뭉개지지 않도록 마스크 조정

