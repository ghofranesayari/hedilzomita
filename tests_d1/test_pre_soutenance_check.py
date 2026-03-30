from pathlib import Path

from scripts.pre_soutenance_check import _check_required_files, _score


def test_score_counts_ok_items():
    checks = [("a", True, ""), ("b", False, ""), ("c", True, "")]
    ok, total = _score(checks)
    assert ok == 2
    assert total == 3


def test_required_files_detects_missing(tmp_path: Path):
    # empty temp project -> most required files should be missing
    checks = _check_required_files(tmp_path)
    assert len(checks) > 0
    assert any(status is False for _, status, _ in checks)
