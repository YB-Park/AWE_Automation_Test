from __future__ import annotations

import time
from pathlib import Path

from .config import AweGuiConfig
from .files import ensure_clean_output_dir, find_new_or_updated_files, has_expected_artifacts, snapshot_files
from .result import BuildResult
from .screenshot import capture_screenshot


def _connect_or_start_designer(config: AweGuiConfig):
    from pywinauto import Application

    # Try to connect first, so repeated tests can reuse an already-open Designer.
    try:
        app = Application(backend="uia").connect(title_re=config.main_window_title_re, timeout=5)
        return app
    except Exception:
        app = Application(backend="uia").start(config.designer_exe)
        app.connect(title_re=config.main_window_title_re, timeout=config.open_timeout_sec)
        return app


def _main_window(app, config: AweGuiConfig):
    return app.window(title_re=config.main_window_title_re)


def _send_open_file(main, input_awj: Path):
    main.set_focus()
    main.type_keys("^o")
    time.sleep(1.0)

    # Standard Windows Open dialog is usually visible globally.
    from pywinauto import Desktop

    dlg = Desktop(backend="uia").window(title_re=".*Open.*|.*열기.*")
    dlg.wait("visible", timeout=15)
    dlg.set_focus()

    # Keyboard approach is often more robust than trying to identify localized controls.
    dlg.type_keys(str(input_awj), with_spaces=True, set_foreground=True)
    dlg.type_keys("{ENTER}")


def _open_generate_dialog(main, config: AweGuiConfig):
    main.set_focus()

    # First try menu selection. Menu names may be invisible in some MATLAB/compiled GUIs,
    # so this may fail; keyboard fallback follows.
    try:
        main.menu_select("Tools->Generate Target Files")
        return
    except Exception:
        pass

    if not config.use_keyboard_fallback:
        raise RuntimeError("Could not open Generate Target Files via menu_select, and keyboard fallback is disabled")

    # Fallback: Alt+T opens Tools in English UI. The item position can vary by version,
    # so this is intentionally a first-pass heuristic.
    main.type_keys("%t")
    time.sleep(0.5)
    # Try a few down counts and Enter. If wrong, the inspect command will help us tune it.
    for _ in range(8):
        main.type_keys("{DOWN}")
        time.sleep(0.05)
    main.type_keys("{ENTER}")


def _click_generate(config: AweGuiConfig):
    from pywinauto import Desktop

    dlg = Desktop(backend="uia").window(title_re=config.generate_dialog_title_re)
    dlg.wait("visible", timeout=20)
    dlg.set_focus()

    # Try to click a button named Generate. If it is localized or not exposed,
    # fall back to Enter.
    for name in ["Generate", "OK", "확인"]:
        try:
            btn = dlg.child_window(title=name, control_type="Button")
            btn.wait("enabled", timeout=2)
            btn.click_input()
            return
        except Exception:
            continue

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
        app = _connect_or_start_designer(config)
        main = _main_window(app, config)
        main.wait("visible", timeout=config.open_timeout_sec)

        result.stage = "open_awj"
        _send_open_file(main, input_path)
        time.sleep(config.load_wait_sec)

        result.stage = "open_generate_dialog"
        _open_generate_dialog(main, config)

        result.stage = "click_generate"
        _click_generate(config)
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
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="failure")

    result.elapsed_sec = round(time.monotonic() - started, 3)
    return result


def inspect_windows(config: AweGuiConfig) -> BuildResult:
    result = BuildResult(ok=True, stage="inspect", message="Window inspection completed")
    try:
        from pywinauto import Desktop

        windows = []
        for w in Desktop(backend="uia").windows():
            try:
                windows.append({"title": w.window_text(), "class_name": w.class_name()})
            except Exception:
                continue
        result.details["windows"] = windows
        result.screenshot = capture_screenshot(config.screenshot_dir, prefix="inspect")
    except Exception as exc:
        result.ok = False
        result.message = f"Inspection failed: {exc}"
        result.errors.append(repr(exc))
    return result
