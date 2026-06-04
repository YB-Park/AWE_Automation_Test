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
                    windows.append({"backend": backend, "title": title, "class_name": class_name})
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


def _active_window():
    from pywinauto import Desktop
    return Desktop(backend="uia").get_active()


def _type_path_and_enter(dlg, input_awj: Path, result: BuildResult):
    path_text = str(input_awj)
    _debug(result, f"Entering AWJ path via clipboard: {path_text}")
    _set_clipboard_text(path_text)
    dlg.set_focus()
    time.sleep(0.3)
    try:
        dlg.type_keys("%n")
        time.sleep(0.2)
    except Exception as exc:
        _debug(result, f"Alt+N failed, continuing: {exc!r}")
    dlg.type_keys("^a")
    time.sleep(0.1)
    dlg.type_keys("^v")
    time.sleep(0.3)
    dlg.type_keys("{ENTER}")


def _wait_for_loaded_design_window(config: AweGuiConfig, input_awj: Path, fallback_win, result: BuildResult):
    from pywinauto import Desktop

    stem_raw = input_awj.stem
    filename_raw = input_awj.name
    pattern = config.loaded_window_title_re_template.format(stem=re.escape(stem_raw), filename=re.escape(filename_raw))
    _debug(result, f"Waiting for loaded design window: {pattern}")

    deadline = time.monotonic() + max(config.load_wait_sec, 5.0)
    last_error = None
    seen = []
    while time.monotonic() < deadline:
        for backend in ["uia", "win32"]:
            try:
                win = Desktop(backend=backend).window(title_re=pattern)
                win.wait("visible", timeout=1)
                _debug(result, f"Loaded design window matched backend={backend}, title={win.window_text()}")
                return win
            except Exception as exc:
                last_error = exc
        try:
            active = _active_window()
            active_title = active.window_text()
            if active_title and active_title not in seen:
                seen.append(active_title)
                _debug(result, f"Active window while waiting: {active_title!r}")
            if stem_raw.lower() in (active_title or "").lower() or filename_raw.lower() in (active_title or "").lower():
                _debug(result, f"Using active window as loaded design window: {active_title!r}")
                return active
        except Exception as exc:
            _debug(result, f"Active window check failed: {exc!r}")
        time.sleep(0.5)

    try:
        current_title = fallback_win.window_text()
        _debug(result, f"Falling back to original window, current title={current_title!r}")
        result.details["loaded_window_fallback"] = "original_window"
        result.details["windows_after_open_file"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
        return fallback_win
    except Exception:
        pass

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

    dlg, backend, pattern = _find_dialog([".*Open Design.*", ".*Open.*|.*열기.*", ".*Select.*|.*선택.*", ".*File.*|.*파일.*"], timeout_sec=20)
    _debug(result, f"Open dialog matched backend={backend}, pattern={pattern}, title={dlg.window_text()}")
    _type_path_and_enter(dlg, input_awj, result)
    return _wait_for_loaded_design_window(config, input_awj, main, result)


def _open_generate_dialog(design_win, config: AweGuiConfig, result: BuildResult):
    design_win.set_focus()
    time.sleep(0.5)
    _debug(result, f"Generate command target window title: {design_win.window_text()!r}")
    _debug(result, "Trying menu_select: Tools->Generate Target Files")
    try:
        design_win.menu_select("Tools->Generate Target Files")
        return
    except Exception as exc:
        _debug(result, f"menu_select failed: {exc!r}")

    if not config.use_keyboard_fallback:
        raise RuntimeError("Could not open Generate Target Files via menu_select, and keyboard fallback is disabled")

    down_count = max(0, int(config.tools_menu_down_count))
    _debug(result, f"Trying keyboard fallback on design window: Alt+T then Down x {down_count} then Enter")
    design_win.type_keys("%t")
    time.sleep(0.8)
    result.details["windows_after_alt_t"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    for _ in range(down_count):
        design_win.type_keys("{DOWN}")
        time.sleep(0.08)
    design_win.type_keys("{ENTER}")


def _read_control_texts(dlg, limit: int = 200) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    try:
        for c in dlg.descendants():
            try:
                text = c.window_text()
            except Exception:
                continue
            text = (text or "").strip()
            if text and text not in seen:
                seen.add(text)
                texts.append(text)
                if len(texts) >= limit:
                    break
    except Exception:
        pass
    return texts


def _snapshot_dialog_controls(dlg, result: BuildResult) -> None:
    controls = []
    try:
        for c in dlg.descendants():
            text = c.window_text()
            ctype = c.friendly_class_name()
            try:
                rect = c.rectangle()
                rect_text = f"{rect.left},{rect.top},{rect.right},{rect.bottom}"
            except Exception:
                rect_text = ""
            if text or ctype in ("Edit", "ComboBox", "Button", "CheckBox"):
                controls.append({"title": text, "control_type": ctype, "rect": rect_text})
    except Exception as exc:
        controls.append({"error": repr(exc)})
    result.details["generate_dialog_controls"] = controls[:160]


def _click_generate(config: AweGuiConfig, result: BuildResult):
    _debug(result, f"Waiting for Generate dialog: {config.generate_dialog_title_re}")
    result.details["windows_before_generate_dialog"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    dlg, backend, pattern = _find_dialog([config.generate_dialog_title_re, ".*Generate.*", ".*Target.*"], timeout_sec=5)
    _debug(result, f"Generate dialog matched backend={backend}, pattern={pattern}, title={dlg.window_text()}")
    dlg.set_focus()
    time.sleep(max(0.0, config.generate_dialog_ready_delay_sec))
    _snapshot_dialog_controls(dlg, result)

    # If tab count is configured, use it first. This is much faster for AWE/MATLAB dialogs
    # where button discovery is visible to humans but unreliable through UI Automation.
    tab_count = max(0, int(config.generate_button_tab_count))
    if tab_count > 0:
        _debug(result, f"Keyboard-first Generate click: Tab x {tab_count}, Space")
        for _ in range(tab_count):
            dlg.type_keys("{TAB}")
            time.sleep(0.04)
        dlg.type_keys("{SPACE}")
        return

    # Fallback: direct UIA/win32 methods.
    for name in ["Generate", "&Generate", "OK", "확인"]:
        try:
            _debug(result, f"Trying child_window button click_input: {name}")
            btn = dlg.child_window(title=name, control_type="Button")
            btn.wait("enabled", timeout=1)
            btn.click_input()
            return
        except Exception as exc:
            _debug(result, f"click_input button {name!r} failed: {exc!r}")

    _debug(result, "Final fallback: Enter in Generate dialog")
    dlg.type_keys("{ENTER}")


def _dismiss_dialog(dlg, result: BuildResult, label: str) -> bool:
    try:
        dlg.set_focus()
        time.sleep(0.15)
        dlg.type_keys("{ENTER}")
        _debug(result, f"Closed {label} dialog with Enter")
        return True
    except Exception as exc:
        _debug(result, f"Enter close failed for {label} dialog: {exc!r}")

    try:
        dlg.close()
        _debug(result, f"Closed {label} dialog with close()")
        return True
    except Exception as exc:
        _debug(result, f"close() failed for {label} dialog: {exc!r}")
        return False


def _inspect_post_generate_dialog(config: AweGuiConfig, result: BuildResult) -> dict[str, object] | None:
    from pywinauto import Desktop

    _debug(result, "Waiting for post-generate success/error dialog")
    deadline = time.monotonic() + max(0.0, config.post_generate_timeout_sec)
    success_pattern = config.generate_dialog_title_re
    error_pattern = config.generate_error_dialog_title_re

    while time.monotonic() < deadline:
        for backend in ["uia", "win32"]:
            for kind, pattern in [("error", error_pattern), ("success", success_pattern)]:
                try:
                    dlg = Desktop(backend=backend).window(title_re=pattern)
                    dlg.wait("visible", timeout=0.5)
                    title = dlg.window_text()
                    texts = _read_control_texts(dlg)
                    # Avoid treating the original Generate dialog as success before it changes.
                    joined = "\n".join(texts)
                    if kind == "success" and "Done. Files generated to:" not in joined:
                        continue
                    _debug(result, f"Post-generate dialog matched kind={kind}, backend={backend}, title={title!r}")
                    closed = False
                    if config.close_result_dialog_after_build:
                        closed = _dismiss_dialog(dlg, result, f"post-generate {kind}")
                    return {"kind": kind, "title": title, "texts": texts, "closed": closed}
                except Exception:
                    continue
        time.sleep(0.5)

    _debug(result, "No post-generate dialog detected before timeout")
    result.details["windows_after_generate_timeout"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
    return None


def _dismiss_possible_save_prompt(result: BuildResult) -> bool:
    from pywinauto import Desktop

    time.sleep(0.5)
    for backend in ["uia", "win32"]:
        try:
            windows = Desktop(backend=backend).windows()
        except Exception:
            continue
        for win in windows:
            try:
                title = win.window_text() or ""
                texts = _read_control_texts(win, limit=50)
                joined = "\n".join([title, *texts]).lower()
                if "save" not in joined and "저장" not in joined:
                    continue

                win.set_focus()
                time.sleep(0.15)
                for button_name in ["No", "&No", "Don't Save", "Do not save", "저장 안 함", "아니요"]:
                    try:
                        btn = win.child_window(title=button_name, control_type="Button")
                        btn.wait("enabled", timeout=0.5)
                        btn.click_input()
                        _debug(result, f"Dismissed save prompt by clicking {button_name!r}")
                        return True
                    except Exception:
                        continue

                try:
                    win.type_keys("%n")
                    _debug(result, "Dismissed save prompt with Alt+N")
                    return True
                except Exception:
                    win.type_keys("n")
                    _debug(result, "Dismissed save prompt with N")
                    return True
            except Exception as exc:
                _debug(result, f"Save prompt inspection failed: {exc!r}")
    return False


def _close_design_window(design_win, result: BuildResult) -> None:
    try:
        title = design_win.window_text()
    except Exception:
        title = "<unknown>"
    _debug(result, f"Closing design window: {title!r}")

    try:
        design_win.set_focus()
        time.sleep(0.2)
        design_win.close()
        _debug(result, "Requested design window close via close()")
    except Exception as exc:
        _debug(result, f"design_win.close() failed: {exc!r}")
        try:
            design_win.type_keys("%{F4}")
            _debug(result, "Requested design window close via Alt+F4")
        except Exception as exc2:
            _debug(result, f"Alt+F4 close failed: {exc2!r}")

    if _dismiss_possible_save_prompt(result):
        time.sleep(0.5)


def build_awj(config: AweGuiConfig, input_awj: str | Path, output_dir: str | Path) -> BuildResult:
    started = time.monotonic()
    input_path = Path(input_awj).resolve()
    out_path = ensure_clean_output_dir(output_dir).resolve()
    result = BuildResult(ok=False, stage="start", message="Build started", input_awj=str(input_path), output_dir=str(out_path))
    design_win = None

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

        result.stage = "read_generate_result"
        post_dialog = _inspect_post_generate_dialog(config, result)
        if post_dialog:
            result.details["post_generate_dialog"] = post_dialog
            if post_dialog.get("kind") == "error":
                result.ok = False
                result.message = "Generate Target Files failed"
                result.errors.extend(str(x) for x in post_dialog.get("texts", []))
                return result

        time.sleep(config.generate_wait_sec)

        result.stage = "verify_artifacts"
        changed = find_new_or_updated_files(out_path, before)
        ok, missing = has_expected_artifacts(changed, config.expected_extensions)
        result.generated_files = changed
        if missing:
            result.warnings.append("Missing expected extensions: " + ", ".join(missing))
        result.ok = ok
        result.message = "Generated expected artifacts" if ok else "Generate step completed, but expected artifacts were not found"

    except Exception as exc:
        result.ok = False
        result.message = f"Automation failed at stage '{result.stage}': {exc}"
        result.errors.append(repr(exc))
        result.details.setdefault("visible_windows_at_failure", _list_windows(config.inspect_title_filter, config.inspect_limit))
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="failure")
    finally:
        if config.close_designer_after_build and design_win is not None:
            try:
                _close_design_window(design_win, result)
            except Exception as exc:
                _debug(result, f"Unexpected design-window cleanup failure: {exc!r}")
        result.elapsed_sec = round(time.monotonic() - started, 3)

    return result


def inspect_windows(config: AweGuiConfig) -> BuildResult:
    result = BuildResult(ok=True, stage="inspect", message="Window inspection completed")
    try:
        result.details["windows"] = _list_windows(config.inspect_title_filter, config.inspect_limit)
        try:
            active = _active_window()
            result.details["active_window"] = {"title": active.window_text(), "class_name": active.class_name()}
        except Exception as exc:
            result.details["active_window_error"] = repr(exc)
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="inspect")
    except Exception as exc:
        result.ok = False
        result.message = f"Inspection failed: {exc}"
        result.errors.append(repr(exc))
    return result
