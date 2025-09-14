Unity WebSocket Client (subscribe /ws/timeline)

Overview
- Unity에서 서버의 실시간 타임라인(`/ws/timeline`)를 직접 구독하는 예시입니다.
- UDP 미러 대신 WebSocket을 쓰면 손실이 적고 양방향 확장이 쉽습니다.

Usage
1) 서버 실행: `powershell -ExecutionPolicy Bypass -File scripts\\run_server.ps1 -BindHost 127.0.0.1 -Port 8000`
2) Unity 프로젝트에 `unity/TimelineWsClient.cs`, `unity/TimelineAnimator.cs` 추가
3) 빈 GameObject에 `TimelineWsClient`와 `TimelineAnimator`를 붙이고, 클라이언트의 `timelineAnimator` 필드에 바인딩
4) `TimelineAnimator`
   - `mappings`: clip→Animator state, 기본 layer 설정
   - `useCrossFade`/`crossFadeDuration`: CrossFade 재생 사용 여부/시간
   - `channelLayers`: 이벤트의 `channel` 값을 레이어 번호로 매핑(선택)

5) 매핑 프리셋(JSON) 사용(선택)
   - 예시 파일: `unity/mappings/example_mappings.json`
   - 로더 스크립트: `unity/TimelineMappingLoader.cs`
   - 사용: Unity에서 TextAsset으로 JSON을 추가하고, `TimelineMappingLoader.mappingJson`에 할당 → `targetAnimator`에 `TimelineAnimator` 바인딩

Notes
- API Key가 필요 없다면 그대로 사용합니다. 필요할 경우 `wsUrl`에 `?key=YOUR_KEY` 쿼리를 붙이세요.
- JSON 파싱 후, 이벤트(`events`)의 `clip`, `t_ms`, `dur_ms`, `channel` 등을 사용해 애니메이션을 구동하세요.
