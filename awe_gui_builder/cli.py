from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .builder import build_awj, inspect_windows
from .config import load_config
from .result import BuildResult


DEFAULT_CONFIG_PATH = Path("configs") / "sample.local.json"


def _compact_result(result: BuildResult) -> dict[str, Any]:
    """Return a stable, LLM-friendly result payload.

    The full BuildResult contains noisy GUI automation diagnostics under
    result.details. Those are useful during selector tuning, but they waste
    tokens when this command is called from an MCP server or an LLM tool.
    """
    post_generate_dialog = result.details.get("post_generate_dialog") if result.details else None

    payload: dict[str, Any] = {
        "ok": result.ok,
        "stage": result.stage,
        "message": result.message,
        "input_awj": result.input_awj,
        "output_dir": result.output_dir,
        "generated_files": result.generated_files,
        "warnings": result.warnings,
        "errors": result.errors,
        "post_generate_dialog": post_generate_dialog,
        "elapsed_sec": result.elapsed_sec,
    }
    return payload


def _print_result(result: BuildResult, verbose: bool) -> None:
    if verbose:
        print(result.to_json())
        return
    print(json.dumps(_compact_result(result), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awe_gui_builder")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="List visible top-level windows and capture a screenshot")
    inspect.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to local JSON config")
    inspect.add_argument("--verbose", action="store_true", help="Print full diagnostic JSON")

    build = sub.add_parser("build", help="Open an AWJ in AWE Designer and run Generate Target Files")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to local JSON config")
    build.add_argument("--input", required=True, help="Input .awj path")
    build.add_argument("--output", required=True, help="Output directory to verify")
    build.add_argument("--verbose", action="store_true", help="Print full diagnostic JSON including UI debug details")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "inspect":
        result = inspect_windows(config)
    elif args.command == "build":
        result = build_awj(config, args.input, args.output)
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    _print_result(result, verbose=bool(getattr(args, "verbose", False)))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
