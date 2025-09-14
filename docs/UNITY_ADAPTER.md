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

Unity Adapter (UDP Mirror)

Overview
- 서버는 기본적으로 WebSocket(`/ws/timeline`)으로 타임라인을 푸시합니다.
- Unity에서도 손쉽게 수신할 수 있도록, 선택적으로 UDP로 동일 JSON을 미러링할 수 있게 했습니다.

Enable UDP Mirror
- 환경변수 설정: `UNITY_UDP_ADDR=127.0.0.1:9001`
- 서버 시작 후, 모든 `timeline`/`timeline.replace` 이벤트가 지정된 UDP 주소로 JSON 라인 형식으로 전송됩니다.

JSON Format
- 동일한 구조가 전송됩니다.
  - timeline: `{ "type":"timeline", "data": { id, events:[{t_ms, dur_ms, clip, channel?}], ... } }`
  - timeline.replace: `{ "type":"timeline.replace", "from_t_ms": N, "data": { id, events:[...] } }`

Unity C# 수신 예시 (간단)
```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class TimelineUdpReceiver : MonoBehaviour
{
    public int port = 9001;
    UdpClient client;

    void Start()
    {
        client = new UdpClient(port);
        client.BeginReceive(ReceiveCallback, null);
    }

    void ReceiveCallback(IAsyncResult ar)
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, port);
        byte[] data = client.EndReceive(ar, ref ep);
        string json = Encoding.UTF8.GetString(data);
        Debug.Log($"Timeline JSON: {json}");
        // TODO: parse JSON and drive animation
        client.BeginReceive(ReceiveCallback, null);
    }

    void OnDestroy()
    {
        client?.Close();
    }
}
```

Notes
- UDP는 신뢰성이 낮으므로, Unity에서 누락에 대비한 보간/보정 로직을 권장합니다.
- 더 안정적인 연동은 WebSocket 클라이언트를 Unity에서 사용하거나, TCP 기반 gRPC/WS를 고려하세요.
