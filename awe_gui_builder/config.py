from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AweGuiConfig:
    designer_exe: str
    main_window_title_re: str = ".*Audio Weaver.*"
    generate_dialog_title_re: str = ".*Generate Target Files.*"
    open_timeout_sec: int = 90
    load_wait_sec: float = 5.0
    generate_wait_sec: float = 20.0
    expected_extensions: tuple[str, ...] = (".awb", ".tsf")
    screenshot_dir: str = "artifacts/screenshots"
    use_keyboard_fallback: bool = True
    close_designer_after_build: bool = False

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AweGuiConfig":
        return AweGuiConfig(
            designer_exe=str(data["designer_exe"]),
            main_window_title_re=str(data.get("main_window_title_re", ".*Audio Weaver.*")),
            generate_dialog_title_re=str(data.get("generate_dialog_title_re", ".*Generate Target Files.*")),
            open_timeout_sec=int(data.get("open_timeout_sec", 90)),
            load_wait_sec=float(data.get("load_wait_sec", 5.0)),
            generate_wait_sec=float(data.get("generate_wait_sec", 20.0)),
            expected_extensions=tuple(data.get("expected_extensions", [".awb", ".tsf"])),
            screenshot_dir=str(data.get("screenshot_dir", "artifacts/screenshots")),
            use_keyboard_fallback=bool(data.get("use_keyboard_fallback", True)),
            close_designer_after_build=bool(data.get("close_designer_after_build", False)),
        )


def load_config(path: str | Path) -> AweGuiConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AweGuiConfig.from_dict(data)
