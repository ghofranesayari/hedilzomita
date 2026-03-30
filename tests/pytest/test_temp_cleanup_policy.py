import os
import time

from ui import shared


class _Uploaded:
    def __init__(self, name: str, payload: bytes):
        self.name = name
        self._payload = payload

    def getbuffer(self):
        return self._payload


def test_save_and_remove_temp_file_with_root_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(shared, "PROJECT_ROOT", tmp_path)

    uploaded = _Uploaded("cv test.pdf", b"hello")
    saved_path = shared.save_temp_file(uploaded, dest_dir="data/temp_uploads")
    assert os.path.exists(saved_path)

    removed = shared.remove_temp_file(saved_path)
    assert removed is True
    assert not os.path.exists(saved_path)


def test_cleanup_temp_dir_removes_old_files(tmp_path, monkeypatch):
    monkeypatch.setattr(shared, "PROJECT_ROOT", tmp_path)
    temp_dir = tmp_path / "data" / "temp_uploads" / "cleanup_test"
    temp_dir.mkdir(parents=True, exist_ok=True)

    old_file = temp_dir / "old.txt"
    new_file = temp_dir / "new.txt"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    old_ts = time.time() - (3 * 3600)
    os.utime(old_file, (old_ts, old_ts))

    stats = shared.cleanup_temp_dir(
        dest_dir="data/temp_uploads/cleanup_test",
        retention_hours=1,
        max_files=10,
    )

    assert stats["removed_old"] >= 1
    assert not old_file.exists()
    assert new_file.exists()
