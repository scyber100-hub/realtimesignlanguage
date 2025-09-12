from packages.ksl_rules import tokenize_ko, ko_to_gloss


def test_sino_korean_numbers_basic():
    toks = tokenize_ko("이십오 1,234")
    glosses = [g for g, _ in ko_to_gloss(toks)]
    assert "NUM_25" in glosses
    assert "NUM_1234" in glosses

