from packages.ksl_rules import tokenize_ko, ko_to_gloss


def test_time_normalization():
    toks = tokenize_ko("오후 12시 30분")
    glosses = [g for g, _ in ko_to_gloss(toks)]
    assert "PM" in glosses
    assert "NUM_12" in glosses and "HOUR" in glosses
    assert "NUM_30" in glosses and "MINUTE" in glosses

