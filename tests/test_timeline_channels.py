from packages.sign_timeline import compile_glosses


def test_face_channel_injection():
    tl = compile_glosses([("BREAKING", 0.9), ("KOREA", 0.9)], start_ms=0, gap_ms=60, include_aux_channels=True)
    faces = [e for e in tl["events"] if e.get("channel") == "face"]
    assert any(e["clip"] == "FACE_ALERT" for e in faces)

