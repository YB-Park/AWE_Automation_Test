from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from .config import AweGuiConfig
from .files import ensure_clean_output_dir, find_new_or_updated_files, has_expected_artifacts, snapshot_files
from .result import BuildResult
from .screenshot import capture_screenshot


def _debug(result: BuildResult, message: str) -> None:
    result.details.setdefault("debug", []).append(message)


def _set_clipboard_text(text: str) -> None:
    # Avoid pyperclip dependency. clip.exe is available on normal Windows installs.
    subprocess.run("clip", input=text, text=True, check=True, shell=True)


def _list_windows(title_filter: str | None = None, limit: int = 200) -> list[dict[str, str]]:
    from pywinauto import Desktop

    windows = []
    rx = re.compile(title_filter, re.IGNORECASE) if title_filter else None
    for backend in ["uia", "win32"]:
        try:
            for w in Desktop(backend=backend).windows():
                try:
                    title = w.window_text()
                    class_name = w.class_name()
                    if rx and not (rx.search(title or "") or rx.search(class_name or "")):
                        continue
                    windows.append({
                        "backend": backend,
                        "title": title,
                        "class_name": class_name,
                    })
                    if len(windows) >= limit:
                        return windows
                except Exception:
                    continue
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

    result.details["visible_windows"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    raise RuntimeError(f"Designer started, but main window did not match {config.main_window_title_re!r}. Last error: {last_error!r}")


def _main_window(app, config: AweGuiConfig):
    return app.window(title_re=config.main_window_title_re)


def _find_dialog(title_patterns: list[str], timeout_sec: float):
    from pywinauto import Desktop

    deadline = time.monotonic() + timeout_sec
    last_error = None
    while time.monotonic() < deadline:
        for backend in ["uia", "win32"]:
            for pattern in title_patterns:
                try:
                    candidate = Desktop(backend=backend).window(title_re=pattern)
                    candidate.wait("visible", timeout=1)
                    return candidate, backend, pattern
                except Exception as exc:
                    last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Dialog not found. patterns={title_patterns!r}, last_error={last_error!r}")


def _type_path_and_enter(dlg, input_awj: Path, result: BuildResult):
    path_text = str(input_awj)
    _debug(result, f"Entering AWJ path via clipboard: {path_text}")
    _set_clipboard_text(path_text)
    dlg.set_focus()
    time.sleep(0.3)

    # Do NOT click guessed Edit/ComboBox controls. On AWE's Open Design dialog that can hit
    # the upper-right search field. Keyboard traversal is more stable for this dialog.
    try:
        dlg.type_keys("%n")  # Common Windows file dialog accelerator: File name
        time.sleep(0.2)
    except Exception as exc:
        _debug(result, f"Alt+N failed, continuing with Ctrl+V fallback: {exc!r}")

    dlg.type_keys("^a")
    time.sleep(0.1)
    dlg.type_keys("^v")
    time.sleep(0.3)
    dlg.type_keys("{ENTER}")


def _wait_for_loaded_design_window(config: AweGuiConfig, input_awj: Path, result: BuildResult):
    from pywinauto import Desktop

    stem = re.escape(input_awj.stem)
    pattern = config.loaded_window_title_re_template.format(stem=stem, filename=re.escape(input_awj.name))
    _debug(result, f"Waiting for loaded design window: {pattern}")

    deadline = time.monotonic() + max(config.load_wait_sec, 5.0)
    last_error = None
    while time.monotonic() < deadline:
        for backend in ["uia", "win32"]:
            try:
                win = Desktop(backend=backend).window(title_re=pattern)
                win.wait("visible", timeout=1)
                _debug(result, f"Loaded design window matched backend={backend}, title={win.window_text()}")
                return win
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)

    result.details["windows_after_open_file"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    raise RuntimeError(f"Could not find loaded design window using pattern {pattern!r}. Last error: {last_error!r}")


def _send_open_file(main, input_awj: Path, config: AweGuiConfig, result: BuildResult):
    _debug(result, "Focusing launcher/main window")
    main.set_focus()
    time.sleep(0.5)

    _debug(result, "Sending Ctrl+O")
    main.type_keys("^o")
    time.sleep(1.0)

    result.details["windows_after_ctrl_o"] = _list_windows(config.inspect_title_filter, config.inspect_limit)

    dialog_patterns = [
        ".*Open Design.*",
        ".*Open.*|.*열기.*",
        ".*Select.*|.*선택.*",
        ".*File.*|.*파일.*",
    ]

    dlg, backend, pattern = _find_dialog(dialog_patterns, timeout_sec=20)
    _debug(result, f"Open dialog matched backend={backend}, pattern={pattern}, title={dlg.window_text()}")

    try:
        controls = []
        for c in dlg.descendants():
            text = c.window_text()
            ctype = c.friendly_class_name()
            if text or ctype in ("Edit", "ComboBox", "Button"):
                controls.append({"title": text, "control_type": ctype})
        result.details["open_dialog_controls"] = controls[:80]
    except Exception as exc:
        result.details["open_dialog_controls_error"] = repr(exc)

    _type_path_and_enter(dlg, input_awj, result)
    return _wait_for_loaded_design_window(config, input_awj, result)


def _open_generate_dialog(design_win, config: AweGuiConfig, result: BuildResult):
    design_win.set_focus()
    time.sleep(0.5)

    _debug(result, "Trying menu_select: Tools->Generate Target Files")
    try:
        design_win.menu_select("Tools->Generate Target Files")
        return
    except Exception as exc:
        _debug(result, f"menu_select failed: {exc!r}")

    if not config.use_keyboard_fallback:
        raise RuntimeError("Could not open Generate Target Files via menu_select, and keyboard fallback is disabled")

    _debug(result, "Trying keyboard fallback on loaded design window: Alt+T then Down x 8 then Enter")
    design_win.type_keys("%t")
    time.sleep(0.8)
    result.details["windows_after_alt_t"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    for _ in range(8):
        design_win.type_keys("{DOWN}")
        time.sleep(0.08)
    design_win.type_keys("{ENTER}")


def _click_generate(config: AweGuiConfig, result: BuildResult):
    _debug(result, f"Waiting for Generate dialog: {config.generate_dialog_title_re}")
    result.details["windows_before_generate_dialog"] = _list_windows(config.inspect_title_filter, config.inspect_limit)

    dlg, backend, pattern = _find_dialog([config.generate_dialog_title_re, ".*Generate.*", ".*Target.*"], timeout_sec=20)
    _debug(result, f"Generate dialog matched backend={backend}, pattern={pattern}, title={dlg.window_text()}")
    dlg.set_focus()

    controls = []
    try:
        for c in dlg.descendants():
            text = c.window_text()
            ctype = c.friendly_class_name()
            if text or ctype in ("Edit", "ComboBox", "Button", "CheckBox"):
                controls.append({"title": text, "control_type": ctype})
    except Exception as exc:
        controls.append({"error": repr(exc)})
    result.details["generate_dialog_controls"] = controls[:120]

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
        _debug(result, f"Launcher/main window title: {main.window_text()}")

        result.stage = "open_awj"
        design_win = _send_open_file(main, input_path, config, result)

        result.stage = "open_generate_dialog"
        _open_generate_dialog(design_win, config, result)

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
                design_win.close()
            except Exception:
                pass

    except Exception as exc:
        result.ok = False
        result.message = f"Automation failed at stage '{result.stage}': {exc}"
        result.errors.append(repr(exc))
        result.details.setdefault("visible_windows_at_failure", _list_windows(config.inspect_title_filter, config.inspect_limit))
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="failure")

    result.elapsed_sec = round(time.monotonic() - started, 3)
    return result


def inspect_windows(config: AweGuiConfig) -> BuildResult:
    result = BuildResult(ok=True, stage="inspect", message="Window inspection completed")
    try:
        result.details["windows"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="inspect")
    except Exception as exc:
        result.ok = False
        result.message = f"Inspection failed: {exc}"
        result.errors.append(repr(exc))
    return result
