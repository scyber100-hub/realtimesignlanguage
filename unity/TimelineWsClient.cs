using System;
using System.Collections;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

public class TimelineWsClient : MonoBehaviour
{
    [Header("Server")]
    public string wsUrl = "ws://127.0.0.1:8000/ws/timeline"; // append ?key=... if API key is enabled

    [Header("Debug")] public bool logMessages = true;
    [Header("Optional Animator Binder")] public TimelineAnimator timelineAnimator;

    private ClientWebSocket _ws;
    private CancellationTokenSource _cts;

    IEnumerator Start()
    {
        _cts = new CancellationTokenSource();
        _ws = new ClientWebSocket();
        var connectTask = _ws.ConnectAsync(new Uri(wsUrl), _cts.Token);
        while (!connectTask.IsCompleted) yield return null;
        if (_ws.State != WebSocketState.Open)
        {
            Debug.LogError("WS connect failed: " + _ws.State);
            yield break;
        }
        Debug.Log("WS connected: " + wsUrl);
        // server expects a first text receive to enter loop; send noop
        var hello = Encoding.UTF8.GetBytes("hello");
        awaitSend(hello);
        // start receive loop
        _ = ReceiveLoop();
    }

    private async Task ReceiveLoop()
    {
        var buf = new byte[64 * 1024];
        while (_ws != null && _ws.State == WebSocketState.Open)
        {
            try
            {
                var seg = new ArraySegment<byte>(buf);
                var res = await _ws.ReceiveAsync(seg, _cts.Token);
                if (res.MessageType == WebSocketMessageType.Close)
                {
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye", CancellationToken.None);
                    break;
                }
                var text = Encoding.UTF8.GetString(buf, 0, res.Count);
                if (logMessages)
                    Debug.Log("Timeline msg: " + text);

                if (timelineAnimator != null)
                {
                    // forward raw JSON to animator binder
                    timelineAnimator.HandleMessageJson(text);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning("WS receive error: " + e.Message);
                await Task.Delay(500);
            }
        }
    }

    private async void awaitSend(byte[] data)
    {
        try
        {
            await _ws.SendAsync(new ArraySegment<byte>(data), WebSocketMessageType.Text, true, _cts.Token);
        }
        catch (Exception e)
        {
            Debug.LogWarning("WS send error: " + e.Message);
        }
    }

    private async void OnDestroy()
    {
        try
        {
            _cts?.Cancel();
            if (_ws != null && _ws.State == WebSocketState.Open)
            {
                await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "exit", CancellationToken.None);
            }
        }
        catch { }
        finally
        {
            _ws?.Dispose();
            _ws = null;
        }
    }
}
