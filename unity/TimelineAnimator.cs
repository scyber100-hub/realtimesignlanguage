using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;

[Serializable]
public class TimelineEventDto
{
    public int t_ms;
    public int dur_ms;
    public string clip;
    public string channel; // optional
}

[Serializable]
public class TimelineDataDto
{
    public string id;
    public TimelineEventDto[] events;
}

[Serializable]
public class TimelineMsgDto
{
    public string type; // "timeline" | "timeline.replace" | others
    public TimelineDataDto data;
    public int from_t_ms; // only for replace
}

[Serializable]
public class ClipMapping
{
    public string clip;        // clip id from timeline JSON
    public string stateName;   // Animator state (Layer state path)
    public int layer = 0;      // Animator layer index
}

public class TimelineAnimator : MonoBehaviour
{
    [Header("Animator")]
    public Animator animator;
    public List<ClipMapping> mappings = new List<ClipMapping>();

    [Header("Timing")]
    public float timeScale = 1.0f; // 1.0 = real-time; <1 slower

    [Header("Playback Options")] public bool useCrossFade = true; public float crossFadeDuration = 0.12f;

    [Serializable]
    public class ChannelLayer
    {
        public string channel;
        public int layer;
    }
    [Header("Channel → Layer (optional)")]
    public List<ChannelLayer> channelLayers = new List<ChannelLayer>();

    private readonly List<Coroutine> _scheduled = new List<Coroutine>();
    private int _baseMs = 0;

    void Awake()
    {
        if (animator == null) animator = GetComponent<Animator>();
    }

    Dictionary<string, ClipMapping> BuildMap()
    {
        var map = new Dictionary<string, ClipMapping>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in mappings)
        {
            if (!string.IsNullOrEmpty(m.clip) && !map.ContainsKey(m.clip))
                map[m.clip] = m;
        }
        return map;
    }

    public void ClearScheduled()
    {
        foreach (var c in _scheduled)
        {
            if (c != null) StopCoroutine(c);
        }
        _scheduled.Clear();
    }

    public void HandleMessageJson(string json)
    {
        try
        {
            var msg = JsonUtility.FromJson<TimelineMsgDto>(json);
            if (msg == null || msg.data == null || msg.data.events == null) return;
            if (msg.type == "timeline")
            {
                // Replace full schedule
                ClearScheduled();
                if (msg.data.events.Length > 0)
                    _baseMs = msg.data.events[0].t_ms;
                ScheduleEvents(msg.data.events);
            }
            else if (msg.type == "timeline.replace")
            {
                // Best-effort: schedule just the replacement slice
                ScheduleEvents(msg.data.events);
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("TimelineAnimator JSON error: " + e.Message);
        }
    }

    void ScheduleEvents(TimelineEventDto[] events)
    {
        var map = BuildMap();
        var now = Time.time;
        foreach (var ev in events)
        {
            if (ev == null || string.IsNullOrEmpty(ev.clip)) continue;
            if (!map.TryGetValue(ev.clip, out var m)) continue; // unmapped clip
            var delaySec = Mathf.Max(0f, ((ev.t_ms - _baseMs) / 1000f) / Mathf.Max(0.0001f, timeScale));
            var state = m.stateName;
            var layer = ResolveLayer(ev, m.layer);
            var co = StartCoroutine(PlayAfter(delaySec, state, layer));
            _scheduled.Add(co);
        }
    }

    int ResolveLayer(TimelineEventDto ev, int defaultLayer)
    {
        if (!string.IsNullOrEmpty(ev.channel))
        {
            foreach (var cl in channelLayers)
            {
                if (!string.IsNullOrEmpty(cl.channel) && string.Equals(cl.channel, ev.channel, StringComparison.OrdinalIgnoreCase))
                    return cl.layer;
            }
        }
        return defaultLayer;
    }

    IEnumerator PlayAfter(float delay, string stateName, int layer)
    {
        if (delay > 0f) yield return new WaitForSeconds(delay);
        try
        {
            if (animator != null && !string.IsNullOrEmpty(stateName))
            {
                if (useCrossFade)
                    animator.CrossFadeInFixedTime(stateName, Mathf.Max(0f, crossFadeDuration), layer, 0f);
                else
                    animator.Play(stateName, layer, 0f);
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Animator play error: {stateName} on layer {layer}: {e.Message}");
        }
    }
}
