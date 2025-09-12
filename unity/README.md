Unity 통합 요약

- `SignTimelinePlayer.cs`를 프로젝트 Assets 폴더에 추가
- 씬에 빈 GameObject 생성 후 컴포넌트 추가
- Animator 참조 연결, ClipId↔Animator StateName 바인딩 등록
- Project Settings > Player > Api Compatibility Level: .NET 4.x
- 실행 전 서버 실행: `scripts/run_server.ps1`
- 타임라인 수신 테스트: `python scripts/example_ws_client.py` 로 메시지 확인 후 Unity 플레이

메시지 처리
- type=="timeline": 전체 타임라인 재생으로 교체
- type=="timeline.replace": from_t_ms 이후 구간을 새 이벤트로 교체(단순 버전은 전체 교체)

