from pathlib import Path

from scripts.build_handover_bundle import _resolve_entries


def test_resolve_entries_marks_present_and_missing(tmp_path: Path):
    (tmp_path / "a.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.txt").write_text("ok", encoding="utf-8")

    included, missing = _resolve_entries(
        project_root=tmp_path,
        relative_paths=["a.txt", "nested/b.txt", "nested/c.txt"],
    )

    included_rel = {str(p.relative_to(tmp_path)).replace("\\", "/") for p in included}
    assert included_rel == {"a.txt", "nested/b.txt"}
    assert missing == ["nested/c.txt"]
