#!/usr/bin/env python3
"""Portable Harness CLI: install, project, and validate the bundle."""
import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path, PurePosixPath

BIN_DIR = Path(__file__).resolve().parent
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))
sys.dont_write_bytecode = True
import validate  # noqa: E402

TEMPLATE_NAME = "portable-harness"
MARKER_BEGIN = "<!-- BEGIN HARNESS MANAGED BLOCK (harness adapt) -->"
MARKER_END = "<!-- END HARNESS MANAGED BLOCK -->"


class MarkerBrokenError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parse_args(argv=None):
    parser = _ArgumentParser(description="Portable Harness CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", description="Install this Harness into a target project."
    )
    init_parser.add_argument("--target", type=Path, required=True)
    init_parser.add_argument("--adapters", default=None)
    init_parser.add_argument("--format", choices=("text", "json"), default="text")

    adapt_parser = subparsers.add_parser(
        "adapt", description="Generate platform projection files."
    )
    adapt_parser.add_argument("--root", type=Path, default=BIN_DIR.parent)
    adapt_parser.add_argument("--check", action="store_true")
    adapt_parser.add_argument("--format", choices=("text", "json"), default="text")

    validate_parser = subparsers.add_parser(
        "validate", description="Validate the Harness contract."
    )
    validate_parser.add_argument("--root", type=Path, default=BIN_DIR.parent)
    validate_parser.add_argument("--format", choices=("text", "json"), default="text")

    return parser.parse_args(argv)


def emit(fmt, command, ok, errors, notices, extra):
    """Render one command result. Returns the exit code (0 ok, 1 violation)."""
    errors = sorted(errors)
    notices = sorted(notices)
    if fmt == "json":
        payload = {
            "ok": ok,
            "command": command,
            "errors": [asdict(item) for item in errors],
            "notices": [asdict(item) for item in notices],
        }
        payload.update(extra)
        sys.stdout.write(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    else:
        for item in errors + notices:
            sys.stdout.write(
                f"[{validate.escape_text_field(item.code)}] "
                f"{validate.escape_text_field(item.path)}: "
                f"{validate.escape_text_field(item.message)}\n"
            )
        for path in extra.get("written", ()):
            sys.stdout.write(f"written: {path}\n")
        if ok:
            sys.stdout.write(f"{command}: ok\n")
    return 0 if ok else 1


def apply_managed_block(existing_text, body):
    """Insert or refresh the managed block; user text outside it is untouched."""
    block = MARKER_BEGIN + "\n" + body + "\n" + MARKER_END + "\n"
    if existing_text is None:
        return block
    begins = existing_text.count(MARKER_BEGIN)
    ends = existing_text.count(MARKER_END)
    if begins == 0 and ends == 0:
        prefix = existing_text
        if not prefix.endswith("\n"):
            prefix += "\n"
        return prefix + "\n" + block
    if begins != 1 or ends != 1:
        raise MarkerBrokenError("managed block markers are broken")
    begin_index = existing_text.index(MARKER_BEGIN)
    end_index = existing_text.index(MARKER_END)
    if end_index < begin_index:
        raise MarkerBrokenError("managed block markers are broken")
    suffix = existing_text[end_index + len(MARKER_END):].lstrip("\n")
    return existing_text[:begin_index] + block + suffix


def render_block_body(manifest):
    entrypoint = manifest["entrypoint"]
    template_dir = manifest["change_management"]["template"]
    lines = [
        "This project uses a portable AI coding harness stored in `.harness/`.",
        "",
        f"- Entrypoint: `.harness/{entrypoint}`",
        "- Manifest: `.harness/manifest.json`",
        "",
        "Components:",
        "",
    ]
    for component in manifest["components"]:
        lines.append(
            f"- {component['id']} ({component['kind']}): `.harness/{component['path']}`"
        )
    lines.extend(
        [
            "",
            "Workflow:",
            "",
            "1. Read the entrypoint, then load only the components needed for the current task.",
            f"2. Deliver changes through a Change Record started from `.harness/{template_dir}/`.",
            "3. Run `python3 .harness/bin/harness.py validate` before delivery.",
            "",
            "Do not edit this block by hand. Regenerate it with `python3 .harness/bin/harness.py adapt`.",
        ]
    )
    return "\n".join(lines)


CURSOR_FRONTMATTER = (
    "---\n"
    "description: Portable AI coding harness entrypoint\n"
    "alwaysApply: true\n"
    "---\n"
    "\n"
)


def render_cursor_file(manifest):
    return (
        CURSOR_FRONTMATTER
        + MARKER_BEGIN
        + "\n"
        + render_block_body(manifest)
        + "\n"
        + MARKER_END
        + "\n"
    )


ADAPTERS = {
    "claude-code": {"path": "CLAUDE.md", "mode": "block"},
    "codex": {"path": "AGENTS.md", "mode": "block"},
    "cursor": {"path": ".cursor/rules/harness.mdc", "mode": "file"},
}


def cmd_validate(root, fmt):
    try:
        result = validate.validate_harness(root)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    rendered = (
        validate.render_json(result) if fmt == "json" else validate.render_text(result)
    )
    sys.stdout.write(rendered)
    return 0 if result.valid else 1


def cmd_adapt(root, check, fmt):
    raise RuntimeError("adapt is implemented in a later task")


def cmd_init(target, adapters_raw, fmt):
    raise RuntimeError("init is implemented in a later task")


def main(argv=None):
    try:
        args = parse_args(argv)
    except ValueError as error:
        sys.stderr.write(f"[ARGUMENT_INVALID] .: {error}\n")
        return 2
    if args.command == "validate":
        return cmd_validate(args.root, args.format)
    if args.command == "adapt":
        return cmd_adapt(args.root, args.check, args.format)
    if args.command == "init":
        return cmd_init(args.target, args.adapters, args.format)
    raise RuntimeError(f"unsupported command {args.command!r}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as error:
        sys.stderr.write(f"[INTERNAL_ERROR] .: {error}\n")
        raise SystemExit(2)
