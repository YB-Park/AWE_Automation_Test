# AWE Copilot Skill

This repository includes a lightweight Copilot-friendly skill for validating Audio Weaver Designer `.awj` files with the local Windows GUI automation wrapper.

## Files

```text
.github/copilot-instructions.md
.github/prompts/awe-build.prompt.md
.github/prompts/awe-debug.prompt.md
docs/AWE_COPILOT_SKILL.md
```

## Demo flow

1. Open this repository in VS Code.
2. Make sure dependencies are installed:

```cmd
scripts\setup-venv.bat
```

3. Validate an AWJ file:

```cmd
scripts\run-build.bat C:\work\test_001_001.awj C:\work\awe_build
```

4. Give the compact JSON output to Copilot Chat or your MCP wrapper.

## Expected compact output

Success:

```json
{
  "ok": true,
  "stage": "verify_artifacts",
  "message": "Generated expected artifacts",
  "input_awj": "C:\\work\\test.awj",
  "output_dir": "C:\\work\\awe_build",
  "generated_files": ["..."],
  "warnings": [],
  "errors": [],
  "post_generate_dialog": {
    "kind": "success",
    "title": "Generate Target Files",
    "texts": ["Done. Files generated to: ..."]
  },
  "elapsed_sec": 4.2
}
```

AWE generation error:

```json
{
  "ok": false,
  "stage": "read_generate_result",
  "message": "Generate Target Files failed",
  "generated_files": [],
  "errors": ["..."],
  "post_generate_dialog": {
    "kind": "error",
    "title": "Generate Target Files Error",
    "texts": ["..."]
  }
}
```

## Copilot usage

In Copilot Chat, ask something like:

```text
Use the AWE build skill to validate C:\work\test_001_001.awj into C:\work\awe_build and summarize the JSON result.
```

For automation debugging:

```text
Use the AWE debug prompt to inspect why the AWE GUI wrapper failed. Do not ask for AWJ contents.
```

## MCP wrapper guidance

Expose a tool that shells out to:

```cmd
python -m awe_gui_builder build --input <awjPath> --output <outputDir>
```

Return stdout as JSON unchanged. The default output is already compact and suitable for LLM consumption.

Use `--verbose` only for debugging the GUI automation itself.

## Important constraints

- Use `cmd.exe` style commands by default.
- Avoid PowerShell by default because it may be blocked by company policy.
- Do not upload or request confidential `.awj` content.
- Treat AWE Designer's `Generate Target Files Error` text as the source of truth.
