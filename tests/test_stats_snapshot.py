from services.pipeline_server import stats


def test_stats_snapshot_keys():
    snap = stats.snapshot()
    assert 'timeline_broadcast_total' in snap
    assert 'ingest_rate_per_sec_1m' in snap
    assert 'latency_ms' in snap
    lm = snap['latency_ms']
    assert isinstance(lm, dict)
    assert 'p50' in lm and 'p90' in lm and 'p99' in lm

