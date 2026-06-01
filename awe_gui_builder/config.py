from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AweGuiConfig:
    designer_exe: str
    main_window_title_re: str = ".*Audio Weaver.*"
    loaded_window_title_re_template: str = ".*{stem}.*"
    generate_dialog_title_re: str = ".*Generate Target Files.*"
    open_timeout_sec: int = 90
    load_wait_sec: float = 5.0
    generate_wait_sec: float = 20.0
    expected_extensions: tuple[str, ...] = (".awb", ".tsf")
    screenshot_dir: str = "artifacts/screenshots"
    use_keyboard_fallback: bool = True
    close_designer_after_build: bool = False
    inspect_title_filter: str = "AWE|Audio|Open|Generate|Target|Design"
    inspect_limit: int = 80

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AweGuiConfig":
        return AweGuiConfig(
            designer_exe=str(data["designer_exe"]),
            main_window_title_re=str(data.get("main_window_title_re", ".*Audio Weaver.*")),
            loaded_window_title_re_template=str(data.get("loaded_window_title_re_template", ".*{stem}.*")),
            generate_dialog_title_re=str(data.get("generate_dialog_title_re", ".*Generate Target Files.*")),
            open_timeout_sec=int(data.get("open_timeout_sec", 90)),
            load_wait_sec=float(data.get("load_wait_sec", 5.0)),
            generate_wait_sec=float(data.get("generate_wait_sec", 20.0)),
            expected_extensions=tuple(data.get("expected_extensions", [".awb", ".tsf"])),
            screenshot_dir=str(data.get("screenshot_dir", "artifacts/screenshots")),
            use_keyboard_fallback=bool(data.get("use_keyboard_fallback", True)),
            close_designer_after_build=bool(data.get("close_designer_after_build", False)),
            inspect_title_filter=str(data.get("inspect_title_filter", "AWE|Audio|Open|Generate|Target|Design")),
            inspect_limit=int(data.get("inspect_limit", 80)),
        )


def load_config(path: str | Path) -> AweGuiConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AweGuiConfig.from_dict(data)
