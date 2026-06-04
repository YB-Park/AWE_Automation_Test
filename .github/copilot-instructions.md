# AWE Designer GUI Builder Skill

You are assisting with an internal PoC that uses Windows GUI automation to validate Audio Weaver Designer `.awj` files by opening them in AWE Designer Standard and running **Tools > Generate Target Files**.

## Primary goal

When asked to validate, build, compile, or check an AWE `.awj` design, use the local automation wrapper in this repository instead of inventing AWE CLI commands.

Preferred command:

```cmd
scripts\run-build.bat C:\path\to\design.awj C:\path\to\output_dir
```

Equivalent Python command:

```cmd
python -m awe_gui_builder build --input C:\path\to\design.awj --output C:\path\to\output_dir
```

Do not require `--config` unless the user says the default config is wrong. The default config is `configs\sample.local.json`.

## Important environment constraints

- Use `cmd.exe` / `.bat` style commands by default.
- Do not suggest PowerShell commands unless the user explicitly asks. PowerShell may be blocked by company policy.
- This tool runs on a real Windows desktop session. It is not headless.
- AWE Designer GUI automation is expected; do not look for or recommend a nonexistent official `.awj` CLI compiler.
- Do not upload, paste, or request confidential `.awj` file contents unless the user explicitly says they are safe to share.

## Output contract

By default, the build command prints compact JSON intended for LLM/MCP consumption:

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

Use `ok`, `message`, `errors`, and `post_generate_dialog` as the primary signals.

## Result interpretation

### Success

If `ok` is `true`, summarize generated artifacts and the output directory. Do not over-explain GUI internals.

### AWE generation error

If `post_generate_dialog.kind` is `error` or `message` is `Generate Target Files failed`, summarize the error lines from `errors` or `post_generate_dialog.texts`. Treat the AWE Designer error output as the source of truth. Do not hallucinate module names, pin names, or graph structure beyond what the error says.

### Missing artifacts

If the Generate step appears to complete but `.awb` or `.tsf` is missing, suggest checking whether AWE Designer generated files to a remembered output directory instead of the requested output directory. The GUI may retain its previous output path.

## Verbose/debug mode

Only request verbose output when diagnosing automation failures:

```cmd
python -m awe_gui_builder build --input C:\path\to\design.awj --output C:\path\to\output_dir --verbose
```

Verbose output may include noisy UI details such as window titles, control lists, screenshots, and debug traces. Do not pass verbose output to an LLM unless needed for automation debugging.

## Common task patterns

### Validate one AWJ

1. Ask for the local `.awj` path and output directory if not provided.
2. Run `scripts\run-build.bat <input.awj> <output_dir>`.
3. Parse the JSON.
4. Report success or summarize AWE Designer errors.

### Prepare an MCP wrapper

Wrap `python -m awe_gui_builder build --input ... --output ...` and return the compact JSON unchanged. Avoid scraping GUI state directly from the MCP server; this repository already handles it.

### Modify automation code

Preserve these working assumptions unless explicitly retuning the UI automation:

- Tools menu fallback uses `tools_menu_down_count`.
- Generate button fallback uses `generate_button_tab_count`.
- The current sample config is tuned for the observed AWE Designer Standard GUI.
- Keep basic command output compact and move diagnostics behind `--verbose`.
