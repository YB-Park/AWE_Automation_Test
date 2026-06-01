from __future__ import annotations

import time
from pathlib import Path

from .config import AweGuiConfig
from .files import ensure_clean_output_dir, find_new_or_updated_files, has_expected_artifacts, snapshot_files
from .result import BuildResult
from .screenshot import capture_screenshot


def _debug(result: BuildResult, message: str) -> None:
    result.details.setdefault("debug", []).append(message)


def _list_windows() -> list[dict[str, str]]:
    from pywinauto import Desktop

    windows = []
    for w in Desktop(backend="uia").windows():
        try:
            windows.append({"title": w.window_text(), "class_name": w.class_name()})
        except Exception:
            continue
    return windows


def _connect_or_start_designer(config: AweGuiConfig, result: BuildResult):
    from pywinauto import Application

    _debug(result, f"Trying to connect to existing Designer: {config.main_window_title_re}")
    try:
        app = Application(backend="uia").connect(title_re=config.main_window_title_re, timeout=5)
        _debug(result, "Connected to existing Designer window")
        return app
    except Exception as exc:
        _debug(result, f"No existing Designer connection: {exc!r}")

    _debug(result, f"Starting Designer: {config.designer_exe}")
    app = Application(backend="uia").start(config.designer_exe)

    deadline = time.monotonic() + config.open_timeout_sec
    last_error = None
    while time.monotonic() < deadline:
        try:
            app.connect(title_re=config.main_window_title_re, timeout=3)
            _debug(result, "Connected after start")
            return app
        except Exception as exc:
            last_error = exc
            time.sleep(1.0)

    result.details["visible_windows"] = _list_windows()
    raise RuntimeError(f"Designer started, but main window did not match {config.main_window_title_re!r}. Last error: {last_error!r}")


def _main_window(app, config: AweGuiConfig):
    return app.window(title_re=config.main_window_title_re)


def _send_open_file(main, input_awj: Path, result: BuildResult):
    from pywinauto import Desktop

    _debug(result, "Focusing main window")
    main.set_focus()
    time.sleep(0.5)

    _debug(result, "Sending Ctrl+O")
    main.type_keys("^o")
    time.sleep(1.5)

    result.details["windows_after_ctrl_o"] = _list_windows()

    dialog_patterns = [
        ".*Open.*|.*열기.*",
        ".*Select.*|.*선택.*",
        ".*File.*|.*파일.*",
    ]

    last_error = None
    dlg = None
    for pattern in dialog_patterns:
        try:
            candidate = Desktop(backend="uia").window(title_re=pattern)
            candidate.wait("visible", timeout=5)
            dlg = candidate
            _debug(result, f"Open dialog matched: {pattern}")
            break
        except Exception as exc:
            last_error = exc

    if dlg is None:
        raise RuntimeError(f"Open dialog did not appear after Ctrl+O. Last error: {last_error!r}")

    dlg.set_focus()
    time.sleep(0.3)

    # Keyboard approach is often more robust than trying to identify localized controls.
    _debug(result, f"Typing AWJ path: {input_awj}")
    dlg.type_keys(str(input_awj), with_spaces=True, set_foreground=True)
    time.sleep(0.2)
    dlg.type_keys("{ENTER}")


def _open_generate_dialog(main, config: AweGuiConfig, result: BuildResult):
    main.set_focus()
    time.sleep(0.5)

    _debug(result, "Trying menu_select: Tools->Generate Target Files")
    try:
        main.menu_select("Tools->Generate Target Files")
        return
    except Exception as exc:
        _debug(result, f"menu_select failed: {exc!r}")

    if not config.use_keyboard_fallback:
        raise RuntimeError("Could not open Generate Target Files via menu_select, and keyboard fallback is disabled")

    _debug(result, "Trying keyboard fallback: Alt+T then Down x 8 then Enter")
    main.type_keys("%t")
    time.sleep(0.8)
    result.details["windows_after_alt_t"] = _list_windows()
    for _ in range(8):
        main.type_keys("{DOWN}")
        time.sleep(0.08)
    main.type_keys("{ENTER}")


def _click_generate(config: AweGuiConfig, result: BuildResult):
    from pywinauto import Desktop

    _debug(result, f"Waiting for Generate dialog: {config.generate_dialog_title_re}")
    result.details["windows_before_generate_dialog"] = _list_windows()

    dlg = Desktop(backend="uia").window(title_re=config.generate_dialog_title_re)
    dlg.wait("visible", timeout=20)
    dlg.set_focus()

    # Capture exposed controls so we can tune selectors after the first failure.
    controls = []
    try:
        for c in dlg.descendants():
            controls.append({"title": c.window_text(), "control_type": c.friendly_class_name()})
    except Exception as exc:
        controls.append({"error": repr(exc)})
    result.details["generate_dialog_controls"] = controls[:200]

    for name in ["Generate", "OK", "확인"]:
        try:
            _debug(result, f"Trying button: {name}")
            btn = dlg.child_window(title=name, control_type="Button")
            btn.wait("enabled", timeout=2)
            btn.click_input()
            return
        except Exception as exc:
            _debug(result, f"Button {name!r} failed: {exc!r}")

    _debug(result, "Falling back to Enter in Generate dialog")
    dlg.type_keys("{ENTER}")


def build_awj(config: AweGuiConfig, input_awj: str | Path, output_dir: str | Path) -> BuildResult:
    started = time.monotonic()
    input_path = Path(input_awj).resolve()
    out_path = ensure_clean_output_dir(output_dir).resolve()

    result = BuildResult(
        ok=False,
        stage="start",
        message="Build started",
        input_awj=str(input_path),
        output_dir=str(out_path),
    )

    if not input_path.exists():
        result.stage = "validate_input"
        result.message = "Input AWJ does not exist"
        result.errors.append(str(input_path))
        result.elapsed_sec = round(time.monotonic() - started, 3)
        return result

    before = snapshot_files(out_path)

    try:
        result.stage = "start_designer"
        app = _connect_or_start_designer(config, result)
        main = _main_window(app, config)
        main.wait("visible", timeout=config.open_timeout_sec)
        _debug(result, f"Main window title: {main.window_text()}")

        result.stage = "open_awj"
        _send_open_file(main, input_path, result)
        time.sleep(config.load_wait_sec)

        result.stage = "open_generate_dialog"
        _open_generate_dialog(main, config, result)

        result.stage = "click_generate"
        _click_generate(config, result)
        time.sleep(config.generate_wait_sec)

        result.stage = "verify_artifacts"
        changed = find_new_or_updated_files(out_path, before)
        ok, missing = has_expected_artifacts(changed, config.expected_extensions)
        result.generated_files = changed
        if missing:
            result.warnings.append("Missing expected extensions: " + ", ".join(missing))

        result.ok = ok
        result.message = "Generated expected artifacts" if ok else "Generate step completed, but expected artifacts were not found"

        if config.close_designer_after_build:
            try:
                main.close()
            except Exception:
                pass

    except Exception as exc:
        result.ok = False
        result.message = f"Automation failed at stage '{result.stage}': {exc}"
        result.errors.append(repr(exc))
        result.details.setdefault("visible_windows_at_failure", _list_windows())
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="failure")

    result.elapsed_sec = round(time.monotonic() - started, 3)
    return result


def inspect_windows(config: AweGuiConfig) -> BuildResult:
    result = BuildResult(ok=True, stage="inspect", message="Window inspection completed")
    try:
        result.details["windows"] = _list_windows()
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="inspect")
    except Exception as exc:
        result.ok = False
        result.message = f"Inspection failed: {exc}"
        result.errors.append(repr(exc))
    return result
