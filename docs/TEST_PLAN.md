# Test Plan

## 0. Clone and install

```powershell
git clone https://github.com/YB-Park/AWE_Automation_Test.git
cd AWE_Automation_Test
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m awe_gui_builder --help
```

Expected: help text appears.

## 1. Configure Designer path

Edit:

```text
configs/sample.local.json
```

Set `designer_exe` to the real AWE Designer executable path.

## 2. Inspect visible windows

Open AWE Designer manually once. Then run:

```powershell
.\scripts\inspect-ui.ps1
```

Expected: JSON output containing visible window titles and a screenshot path.

If the main AWE window title does not match `.*Audio Weaver.*`, update `main_window_title_re`.

## 3. Build attempt

Prepare a non-confidential test AWJ and an empty output directory.

```powershell
.\scripts\run-build.ps1 -InputAwj C:\work\test.awj -OutputDir C:\work\awe_build
```

Expected, eventually:

```json
{
  "ok": true,
  "stage": "verify_artifacts",
  "generated_files": ["...awb", "...tsf"]
}
```

First run may fail. If it fails, keep the JSON output and screenshot. The most likely fixes are:

- Update `main_window_title_re`.
- Update `generate_dialog_title_re`.
- Increase `load_wait_sec` or `generate_wait_sec`.
- Replace the Tools menu fallback sequence in `builder.py` after observing the actual menu behavior.

## 4. Important limitation

This tool currently does not know how to set the output directory inside AWE Designer's Generate Target Files dialog. The first practical test should use whatever output directory Designer already remembers from manual use.

Once we know the dialog structure, we can add output directory selection automation.
