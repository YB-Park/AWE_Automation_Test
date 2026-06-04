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
    generate_error_dialog_title_re: str = ".*Generate Target Files Error.*"
    open_timeout_sec: int = 90
    open_dialog_after_ctrl_o_delay_sec: float = 0.5
    load_wait_sec: float = 5.0
    generate_wait_sec: float = 20.0
    expected_extensions: tuple[str, ...] = (".awb", ".tsf")
    screenshot_dir: str = "artifacts/screenshots"
    use_keyboard_fallback: bool = True
    close_designer_after_build: bool = True
    close_result_dialog_after_build: bool = True
    close_lingering_generate_dialog_after_build: bool = True
    inspect_title_filter: str = "AWE|Audio|Open|Generate|Target|Design|Error|Done|Save|Confirm"
    inspect_limit: int = 80
    tools_menu_down_count: int = 2
    generate_button_tab_count: int = 0
    generate_dialog_ready_delay_sec: float = 1.5
    post_generate_timeout_sec: float = 30.0

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AweGuiConfig":
        return AweGuiConfig(
            designer_exe=str(data["designer_exe"]),
            main_window_title_re=str(data.get("main_window_title_re", ".*Audio Weaver.*")),
            loaded_window_title_re_template=str(data.get("loaded_window_title_re_template", ".*{stem}.*")),
            generate_dialog_title_re=str(data.get("generate_dialog_title_re", ".*Generate Target Files.*")),
            generate_error_dialog_title_re=str(data.get("generate_error_dialog_title_re", ".*Generate Target Files Error.*")),
            open_timeout_sec=int(data.get("open_timeout_sec", 90)),
            open_dialog_after_ctrl_o_delay_sec=float(data.get("open_dialog_after_ctrl_o_delay_sec", 0.5)),
            load_wait_sec=float(data.get("load_wait_sec", 5.0)),
            generate_wait_sec=float(data.get("generate_wait_sec", 20.0)),
            expected_extensions=tuple(data.get("expected_extensions", [".awb", ".tsf"])),
            screenshot_dir=str(data.get("screenshot_dir", "artifacts/screenshots")),
            use_keyboard_fallback=bool(data.get("use_keyboard_fallback", True)),
            close_designer_after_build=bool(data.get("close_designer_after_build", True)),
            close_result_dialog_after_build=bool(data.get("close_result_dialog_after_build", True)),
            close_lingering_generate_dialog_after_build=bool(data.get("close_lingering_generate_dialog_after_build", True)),
            inspect_title_filter=str(data.get("inspect_title_filter", "AWE|Audio|Open|Generate|Target|Design|Error|Done|Save|Confirm")),
            inspect_limit=int(data.get("inspect_limit", 80)),
            tools_menu_down_count=int(data.get("tools_menu_down_count", 2)),
            generate_button_tab_count=int(data.get("generate_button_tab_count", 0)),
            generate_dialog_ready_delay_sec=float(data.get("generate_dialog_ready_delay_sec", 1.5)),
            post_generate_timeout_sec=float(data.get("post_generate_timeout_sec", 30.0)),
        )


def load_config(path: str | Path) -> AweGuiConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AweGuiConfig.from_dict(data)
