using System;
using System.Collections;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Serialization;

public class SignTimelinePlayer : MonoBehaviour
{
    [Header("WebSocket")] public string serverUrl = "ws://localhost:8000/ws/timeline";

    [Header("Animator")] public Animator animator;

    [Serializable]
    public class ClipBinding
    {
        public string clipId;
        public string stateName; // Animator state path
    }

    [Header("Bindings")] public List<ClipBinding> bindings = new List<ClipBinding>();

    private readonly Dictionary<string, string> _map = new Dictionary<string, string>();
    private readonly List<TimelineEvent> _scheduled = new List<TimelineEvent>();
    private CancellationTokenSource _cts;

    [Serializable]
    public class TimelineEvent
    {
        public int t_ms;
        public string clip;
        public int dur_ms;
        public string channel;
    }

    [Serializable]
    public class Timeline
    {
        public string id;
        public long created_ms;
        public List<TimelineEvent> events;
    }

    private void Awake()
    {
        foreach (var b in bindings)
        {
            if (!_map.ContainsKey(b.clipId)) _map.Add(b.clipId, b.stateName);
        }
    }

    private void OnEnable()
    {
        _cts = new CancellationTokenSource();
        _ = RunWebSocket(_cts.Token);
    }

    private void OnDisable()
    {
        _cts?.Cancel();
    }

    private IEnumerator PlayTimeline(Timeline tl)
    {
        var start = Time.realtimeSinceStartup;
        foreach (var ev in tl.events)
        {
            var tSec = ev.t_ms / 1000f;
            // skip past events
            var now = Time.realtimeSinceStartup - start;
            var wait = tSec - now;
            if (wait > 0) yield return new WaitForSecondsRealtime(wait);

            if (_map.TryGetValue(ev.clip, out var state))
            {
                animator.Play(state, 0, 0f);
            }
            else
            {
                // fallback: state name == clip id
                animator.Play(ev.clip, 0, 0f);
            }
        }
    }

    private void ReplaceFrom(int fromMs, List<TimelineEvent> events)
    {
        // 단순 구현: 현재 코루틴은 새 전체 재생으로 교체
        StopAllCoroutines();
        var tl = new Timeline {id = Guid.NewGuid().ToString(), created_ms = NowMs(), events = events};
        StartCoroutine(PlayTimeline(tl));
    }

    private static long NowMs() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

    private async Task RunWebSocket(CancellationToken ct)
    {
        var client = new ClientWebSocket();
        await client.ConnectAsync(new Uri(serverUrl), ct);

        var buffer = new byte[32 * 1024];
        var sb = new StringBuilder();
        while (!ct.IsCancellationRequested && client.State == WebSocketState.Open)
        {
            sb.Length = 0;
            WebSocketReceiveResult result;
            do
            {
                result = await client.ReceiveAsync(new ArraySegment<byte>(buffer), ct);
                if (result.MessageType == WebSocketMessageType.Close) break;
                sb.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
            } while (!result.EndOfMessage);

            var json = sb.ToString();
            try
            {
                var root = JsonUtility.FromJson<Root>(json);
                if (root.type == "timeline" && root.data != null)
                {
                    StopAllCoroutines();
                    StartCoroutine(PlayTimeline(root.data));
                }
                else if (root.type == "timeline.replace" && root.dataReplace != null)
                {
                    ReplaceFrom(root.from_t_ms, root.dataReplace.events);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning($"WS parse error: {e.Message}\n{json}");
            }
        }
    }

    [Serializable]
    private class Root
    {
        public string type;
        public int from_t_ms;
        public Timeline data; // for type==timeline
        public DataReplace dataReplace; // for type==timeline.replace
    }

    [Serializable]
    private class DataReplace
    {
        public string id;
        public List<TimelineEvent> events;
    }
}

