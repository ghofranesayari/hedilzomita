import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile


BUNDLE_RELATIVE_PATHS = [
    "Guide_Utilisation.md",
    "Demarrer_The_Sovereign.bat",
    ".env.example",
    "requirements.lock",
    "pyproject.toml",
    "scripts/install_env.bat",
    "scripts/install_env.ps1",
    "scripts/preflight.py",
    "scripts/test_e1_pack.ps1",
    "scripts/test_e2_checklist.ps1",
    "scripts/test_e3_dryrun.ps1",
    "scripts/test_e4_qa.ps1",
    "outputs/soutenance/SOUTENANCE_1PAGE.md",
    "outputs/soutenance/SOUTENANCE_DETAILLEE.md",
    "outputs/soutenance/SOUTENANCE_ARCHITECTURE.mmd",
    "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.md",
    "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json",
    "outputs/soutenance/DRY_RUN_SOUTENANCE.md",
    "outputs/soutenance/DRY_RUN_SOUTENANCE.json",
    "outputs/soutenance/QA_JURY.md",
]


def _resolve_entries(project_root: Path, relative_paths: List[str]) -> Tuple[List[Path], List[str]]:
    included: List[Path] = []
    missing: List[str] = []
    for rel in relative_paths:
        p = project_root / rel
        if p.exists() and p.is_file():
            included.append(p)
        else:
            missing.append(rel)
    return included, missing


def _build_manifest(
    included: List[Path],
    missing: List[str],
    project_root: Path,
    zip_name: str,
) -> Dict[str, object]:
    return {
        "protocol_version": "e5_handover_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "zip_name": zip_name,
        "included_count": len(included),
        "missing_count": len(missing),
        "included_files": [str(p.relative_to(project_root)).replace("\\", "/") for p in included],
        "missing_files": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a handover zip bundle for supervisors")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--out-dir", default="outputs/soutenance")
    parser.add_argument("--zip-name", default="AEBM_HANDOVER_PACKAGE.zip")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    out_dir = (project_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    included, missing = _resolve_entries(project_root, BUNDLE_RELATIVE_PATHS)

    zip_path = out_dir / args.zip_name
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for p in included:
            arcname = str(p.relative_to(project_root)).replace("\\", "/")
            zf.write(p, arcname=arcname)

    manifest = _build_manifest(
        included=included,
        missing=missing,
        project_root=project_root,
        zip_name=args.zip_name,
    )
    manifest_path = out_dir / "HANDOVER_BUNDLE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[E5] Bundle  : {zip_path}")
    print(f"[E5] Manifest: {manifest_path}")
    print(f"[E5] Included files: {len(included)}")
    if missing:
        print(f"[E5] Missing files : {len(missing)} (check manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
