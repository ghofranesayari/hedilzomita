import pytest

from src.memory.vector_db import VectorDBManager


def test_manifest_detects_tampered_file(tmp_path):
    manager = VectorDBManager.__new__(VectorDBManager)

    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.json"
    f1.write_bytes(b"abc")
    f2.write_text('{"x": 1}', encoding="utf-8")

    manifest = manager._build_integrity_manifest([str(f1), str(f2)])
    manager._verify_integrity_manifest(manifest, [str(f1), str(f2)])

    # Tamper after manifest generation
    f2.write_text('{"x": 2}', encoding="utf-8")

    with pytest.raises(ValueError):
        manager._verify_integrity_manifest(manifest, [str(f1), str(f2)])
