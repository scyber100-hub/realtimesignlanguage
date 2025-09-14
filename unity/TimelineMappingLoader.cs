using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class MappingEntry
{
    public string clip;
    public string stateName;
    public int layer = 0;
}

[Serializable]
public class ChannelLayerEntry
{
    public string channel;
    public int layer;
}

[Serializable]
public class MappingPreset
{
    public List<MappingEntry> mappings = new List<MappingEntry>();
    public List<ChannelLayerEntry> channelLayers = new List<ChannelLayerEntry>();
    public bool useCrossFade = true;
    public float crossFadeDuration = 0.12f;
}

public class TimelineMappingLoader : MonoBehaviour
{
    [Header("Preset (TextAsset JSON)")]
    public TextAsset mappingJson;
    public TimelineAnimator targetAnimator;

    void Awake()
    {
        if (targetAnimator == null) targetAnimator = GetComponent<TimelineAnimator>();
        if (targetAnimator == null || mappingJson == null) return;
        try
        {
            var preset = JsonUtility.FromJson<MappingPreset>(mappingJson.text);
            if (preset == null) return;

            // Apply CrossFade options
            targetAnimator.useCrossFade = preset.useCrossFade;
            targetAnimator.crossFadeDuration = preset.crossFadeDuration;

            // Apply mappings
            targetAnimator.mappings.Clear();
            foreach (var m in preset.mappings)
            {
                targetAnimator.mappings.Add(new ClipMapping { clip = m.clip, stateName = m.stateName, layer = m.layer });
            }

            // Apply channel layers
            targetAnimator.channelLayers.Clear();
            foreach (var cl in preset.channelLayers)
            {
                targetAnimator.channelLayers.Add(new TimelineAnimator.ChannelLayer { channel = cl.channel, layer = cl.layer });
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("TimelineMappingLoader error: " + e.Message);
        }
    }
}

