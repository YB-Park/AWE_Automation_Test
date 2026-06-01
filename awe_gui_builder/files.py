from __future__ import annotations

from pathlib import Path


def ensure_clean_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot_files(output_dir: str | Path) -> dict[str, float]:
    path = Path(output_dir)
    if not path.exists():
        return {}
    return {str(p.resolve()): p.stat().st_mtime for p in path.rglob("*") if p.is_file()}


def find_new_or_updated_files(output_dir: str | Path, before: dict[str, float]) -> list[str]:
    path = Path(output_dir)
    if not path.exists():
        return []
    changed: list[str] = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        full = str(p.resolve())
        old_mtime = before.get(full)
        if old_mtime is None or p.stat().st_mtime > old_mtime:
            changed.append(full)
    return sorted(changed)


def has_expected_artifacts(files: list[str], expected_extensions: tuple[str, ...]) -> tuple[bool, list[str]]:
    lower_files = [f.lower() for f in files]
    missing = []
    for ext in expected_extensions:
        if not any(f.endswith(ext.lower()) for f in lower_files):
            missing.append(ext)
    return len(missing) == 0, missing
