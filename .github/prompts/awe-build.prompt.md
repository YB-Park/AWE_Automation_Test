---
description: Validate an AWE Designer AWJ file using the local GUI automation wrapper
---

# AWE AWJ Build / Validation

Use this prompt when the user wants to validate, build, compile, or check an Audio Weaver Designer `.awj` file.

## What to do

Run the local wrapper from `cmd.exe` style commands:

```cmd
scripts\run-build.bat ${input:awjPath} ${input:outputDir}
```

If invoking Python directly:

```cmd
python -m awe_gui_builder build --input ${input:awjPath} --output ${input:outputDir}
```

Do not require `--config` unless the default config is wrong.

## Inputs

- `awjPath`: absolute path to the `.awj` file.
- `outputDir`: absolute path to the directory where generated target files should be checked.

## How to answer

Read the JSON printed by the command.

If `ok` is true:

- Say the AWJ generated target files successfully.
- Include generated files if present.
- Include the output directory.

If `ok` is false:

- Say the AWE Generate Target Files step failed or did not produce expected artifacts.
- Summarize `errors` and `post_generate_dialog.texts`.
- Do not infer graph structure beyond the error text.

## Debugging

Use verbose mode only when the automation itself fails:

```cmd
python -m awe_gui_builder build --input ${input:awjPath} --output ${input:outputDir} --verbose
```

Verbose output is noisy and should not be the default for LLM/MCP calls.
