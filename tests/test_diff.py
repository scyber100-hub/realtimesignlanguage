from services.pipeline_server import _diff_window


def test_diff_window_basic():
    old = ["A","B","C","D"]
    new = ["A","B","X","D"]
    s,e = _diff_window(old,new)
    assert s == 2 and e == 3


def test_diff_window_suffix_growth():
    old = ["A","B"]
    new = ["A","B","C","D"]
    s,e = _diff_window(old,new)
    assert s == 2 and e == 4


def test_diff_window_prefix_change():
    old = ["A","B","C"]
    new = ["X","B","C"]
    s,e = _diff_window(old,new)
    assert s == 0 and e == 1

