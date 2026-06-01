from __future__ import annotations

from datetime import datetime
from pathlib import Path


def capture_screenshot(output_dir: str | Path, prefix: str = "screenshot") -> str | None:
    try:
        from PIL import ImageGrab

        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = path / f"{prefix}_{stamp}.png"
        image = ImageGrab.grab()
        image.save(target)
        return str(target.resolve())
    except Exception:
        return None
