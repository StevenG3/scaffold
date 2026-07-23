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


def run_adapt(root, manifest, check):
    """Project the manifest into platform files. Root must already be validated."""
    project_root = root.parent
    errors, notices, written, unchanged, stale = [], [], [], [], []
    for name in manifest.get("adapters", []):
        if name not in ADAPTERS:
            notices.append(
                validate.ContractError(
                    "ADAPTER_EXTERNAL",
                    name,
                    "external adapter is not generated by this tool",
                )
            )
            continue
        spec = ADAPTERS[name]
        rel = PurePosixPath(spec["path"])
        target = project_root.joinpath(*rel.parts)
        display = rel.as_posix()
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        if spec["mode"] == "file":
            expected = render_cursor_file(manifest)
        else:
            try:
                expected = apply_managed_block(existing, render_block_body(manifest))
            except MarkerBrokenError:
                errors.append(
                    validate.ContractError(
                        "PROJECTION_MARKER_BROKEN",
                        display,
                        "managed block markers are missing their pair or out of order",
                    )
                )
                continue
        if check:
            if existing is None:
                stale.append(display)
                errors.append(
                    validate.ContractError(
                        "PROJECTION_MISSING", display, "projection file does not exist"
                    )
                )
            elif existing != expected:
                stale.append(display)
                errors.append(
                    validate.ContractError(
                        "PROJECTION_STALE",
                        display,
                        "projection is out of date; run adapt",
                    )
                )
            else:
                unchanged.append(display)
        else:
            if existing == expected:
                unchanged.append(display)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(expected, encoding="utf-8")
                written.append(display)
    return errors, notices, written, unchanged, stale


def cmd_adapt(root, check, fmt):
    try:
        result = validate.validate_harness(root)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    if not result.valid:
        return emit(
            fmt,
            "adapt",
            False,
            list(result.errors),
            [],
            {"written": [], "unchanged": [], "stale": []},
        )
    root = result.root
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("origin") is None:
        notices = [
            validate.ContractError(
                "ADAPT_SKIPPED_TEMPLATE",
                ".",
                "origin is null; template bundles do not generate projections",
            )
        ]
        return emit(
            fmt,
            "adapt",
            True,
            [],
            notices,
            {"written": [], "unchanged": [], "stale": []},
        )
    errors, notices, written, unchanged, stale = run_adapt(root, manifest, check)
    return emit(
        fmt,
        "adapt",
        not errors,
        errors,
        notices,
        {"written": written, "unchanged": unchanged, "stale": stale},
    )


def _parse_adapters_argument(raw, errors):
    names = [item.strip() for item in raw.split(",") if item.strip()]
    seen = set()
    for name in names:
        is_builtin = name in ADAPTERS
        is_extension = name.startswith("x-") and len(name) > 2
        if not (is_builtin or is_extension) or name in seen:
            errors.append(
                validate.ContractError(
                    "ARGUMENT_INVALID",
                    name,
                    "adapter names must be built-in or start with 'x-' and be unique",
                )
            )
        seen.add(name)
    return names


def _init_failure(fmt, errors, notices=(), target=None):
    return emit(
        fmt,
        "init",
        False,
        errors,
        list(notices),
        {"target": target, "projected_files": []},
    )


def cmd_init(target, adapters_raw, fmt):
    source = BIN_DIR.parent
    adapters_override = None
    if adapters_raw is not None:
        argument_errors = []
        adapters_override = _parse_adapters_argument(adapters_raw, argument_errors)
        if argument_errors:
            for item in sorted(argument_errors):
                sys.stderr.write(
                    f"[{item.code}] {item.path}: {item.message}\n"
                )
            return 2

    try:
        source_result = validate.validate_harness(source)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    if not source_result.valid:
        errors = list(source_result.errors)
        errors.append(
            validate.ContractError(
                "INIT_SOURCE_INVALID",
                ".",
                "source template failed validation; refusing to copy",
            )
        )
        return _init_failure(fmt, errors)

    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if "template_version" not in source_manifest:
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_SOURCE_INVALID",
                    "manifest.json",
                    "template_version is required to initialize a project",
                )
            ],
        )

    if not target.is_dir():
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_TARGET_MISSING",
                    str(target),
                    "target must be an existing directory",
                )
            ],
        )
    destination = target / ".harness"
    if destination.exists():
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_TARGET_EXISTS",
                    str(destination),
                    "a .harness directory already exists; refusing to overwrite",
                )
            ],
            target=str(destination),
        )

    shutil.copytree(
        source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    cleanup_hint = validate.ContractError(
        "INIT_CLEANUP_HINT",
        str(destination),
        "initialization failed after copying; remove this directory to retry",
    )

    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    manifest["origin"] = {
        "template_name": TEMPLATE_NAME,
        "template_version": source_manifest["template_version"],
        "initialized_at_schema": manifest["schema_version"],
    }
    if adapters_override is not None:
        manifest["adapters"] = adapters_override
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    errors, notices, written, unchanged, stale = run_adapt(
        destination, manifest, check=False
    )
    if errors:
        return _init_failure(
            fmt, errors, notices=[cleanup_hint] + notices, target=str(destination)
        )

    final_result = validate.validate_harness(destination)
    if not final_result.valid:
        return _init_failure(
            fmt,
            list(final_result.errors),
            notices=[cleanup_hint],
            target=str(destination),
        )

    return emit(
        fmt,
        "init",
        True,
        [],
        notices,
        {
            "target": str(destination.resolve()),
            "projected_files": written + unchanged,
        },
    )


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
