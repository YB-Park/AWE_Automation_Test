from __future__ import annotations

import argparse
import sys

from .builder import build_awj, inspect_windows
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awe_gui_builder")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="List visible top-level windows and capture a screenshot")
    inspect.add_argument("--config", required=True, help="Path to local JSON config")

    build = sub.add_parser("build", help="Open an AWJ in AWE Designer and run Generate Target Files")
    build.add_argument("--config", required=True, help="Path to local JSON config")
    build.add_argument("--input", required=True, help="Input .awj path")
    build.add_argument("--output", required=True, help="Output directory to verify")

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

    print(result.to_json())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
