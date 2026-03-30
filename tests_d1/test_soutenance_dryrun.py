from scripts.build_soutenance_dryrun import build_timeline


def test_timeline_order_and_bounds():
    timeline = build_timeline(total_minutes=15)
    assert len(timeline) > 0
    assert timeline[0]["start_min"] == 0
    assert timeline[-1]["end_min"] == 15

    prev_end = 0
    for item in timeline:
        assert item["start_min"] >= prev_end
        assert item["end_min"] >= item["start_min"]
        prev_end = item["end_min"]


def test_timeline_contains_live_demo_commands():
    timeline = build_timeline(total_minutes=15)
    commands = [item.get("command") for item in timeline if item.get("command")]
    assert any("test_d3.ps1" in cmd for cmd in commands)
    assert any("test_d6_calibration.ps1" in cmd for cmd in commands)
