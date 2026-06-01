# AWE Automation Test

Experimental Windows GUI automation wrapper for Audio Weaver Designer Standard.

Goal:

```text
.awj file
  -> open in AWE Designer GUI
  -> Tools > Generate Target Files
  -> verify generated artifacts
  -> return machine-readable JSON result
```

This repository intentionally starts small. The first milestone is not a perfect automation, but a repeatable local test harness that can tell us which parts of the AWE Designer UI are automatable on the target Windows PC.

## Quick start

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m awe_gui_builder --help
python -m awe_gui_builder inspect --config .\configs\sample.local.json
```

After editing `configs/sample.local.json` for your PC:

```powershell
python -m awe_gui_builder build --config .\configs\sample.local.json --input C:\work\candidate.awj --output C:\work\awe_build
```

## Current status

- JSON result model exists.
- Config loading exists.
- Output artifact verification exists.
- Screenshot capture exists.
- GUI automation is a conservative first pass using `pywinauto` plus keyboard fallback.

Expect the first run to reveal missing window titles, button names, or menu behavior. That is the point of this repo.

## Safety notes

- Run on a dedicated Windows desktop session if possible.
- Use 100% DPI for the first tests.
- Do not run while editing an important unsaved AWE project.
- Keep test `.awj` files and output directories outside any confidential source tree if you later make this repo public.
