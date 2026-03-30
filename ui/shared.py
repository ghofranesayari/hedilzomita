import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fix_mojibake_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    fixed = value
    for _ in range(2):
        if any(token in fixed for token in ("Ã", "Â", "â", "ð", "�")):
            try:
                recoded = fixed.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
                if recoded:
                    fixed = recoded
            except Exception:
                break
        else:
            break

    replacements = {
        "âœ…": "OK",
        "âŒ": "KO",
        "âš ï¸": "WARN",
        "ðŸŸ¢": "OK",
        "ðŸŸ£": "INF",
        "ðŸ”¬": "AI",
    }
    for bad, good in replacements.items():
        fixed = fixed.replace(bad, good)
    return fixed


def normalize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: normalize_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_payload(v) for v in value]
    if isinstance(value, str):
        return fix_mojibake_text(value)
    return value


def _sanitize_filename(filename: str) -> str:
    base = Path(filename or "upload.bin").name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe or "upload.bin"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _resolve_in_project(path_like: str) -> Path:
    p = Path(path_like)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


def save_temp_file(uploaded_file, dest_dir: str = "data/temp_uploads") -> str:
    dest = _resolve_in_project(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(getattr(uploaded_file, "name", "upload.bin"))
    unique_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe_name}"
    path = dest / unique_name

    with open(path, "wb") as file_obj:
        file_obj.write(uploaded_file.getbuffer())
    return str(path)


def remove_temp_file(path: str, allowed_roots: tuple = ("data/temp_uploads", "data/temp_b2b")) -> bool:
    if not path:
        return False

    target = _resolve_in_project(path)
    if not target.exists() or not target.is_file():
        return False

    root_paths = [_resolve_in_project(root) for root in allowed_roots]
    if not any(_is_relative_to(target, root) for root in root_paths):
        return False

    try:
        target.unlink()
        return True
    except Exception:
        return False


def cleanup_temp_dir(
    dest_dir: str = "data/temp_uploads",
    retention_hours: int = 24,
    max_files: int = 200,
) -> Dict[str, int]:
    """
    Cleanup policy:
    - Delete files older than retention_hours.
    - Keep only max_files most recent files.
    """
    removed_old = 0
    removed_excess = 0

    temp_dir = _resolve_in_project(dest_dir)
    if not temp_dir.exists():
        return {"removed_old": 0, "removed_excess": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, retention_hours))

    files = [p for p in temp_dir.rglob("*") if p.is_file()]

    # 1) Retention window cleanup
    for file_path in files:
        if not _is_relative_to(file_path, temp_dir):
            continue
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            try:
                file_path.unlink()
                removed_old += 1
            except Exception:
                pass

    # refresh after old cleanup
    files = [p for p in temp_dir.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # 2) Hard cap on number of files
    if len(files) > max_files:
        for file_path in files[max_files:]:
            if not _is_relative_to(file_path, temp_dir):
                continue
            try:
                file_path.unlink()
                removed_excess += 1
            except Exception:
                pass

    # 3) Remove empty directories
    for subdir in sorted([p for p in temp_dir.rglob("*") if p.is_dir()], reverse=True):
        try:
            subdir.rmdir()
        except Exception:
            pass

    return {"removed_old": removed_old, "removed_excess": removed_excess}
