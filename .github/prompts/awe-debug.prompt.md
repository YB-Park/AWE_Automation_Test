---
description: Debug the AWE Designer GUI automation wrapper when normal build automation fails
---

# AWE GUI Automation Debug

Use this prompt only when the automation wrapper fails before or during GUI control, not when AWE Designer reports a normal design-generation error.

## First command

```cmd
scripts\inspect-ui.bat
```

This prints verbose UI/window details by design.

## Verbose build command

```cmd
python -m awe_gui_builder build --input ${input:awjPath} --output ${input:outputDir} --verbose
```

## What to inspect

Focus on these fields:

- `stage`
- `message`
- `details.debug`
- `details.visible_windows_at_failure`
- `details.windows_after_ctrl_o`
- `details.windows_after_alt_t`
- `details.generate_dialog_controls`
- `screenshot`

## Common fixes

- If AWE Designer main window is not found, tune `main_window_title_re` in `configs\sample.local.json`.
- If Tools menu opens but wrong item is selected, tune `tools_menu_down_count`.
- If Generate dialog opens but the Generate button is not pressed, tune `generate_button_tab_count`.
- If generation succeeds but artifacts are missing, check whether AWE Designer used a remembered output directory.

## Constraints

- Prefer `.bat` / `cmd.exe` commands.
- Do not suggest PowerShell by default.
- Do not request confidential `.awj` file contents.
