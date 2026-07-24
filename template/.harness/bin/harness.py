#!/usr/bin/env python3
"""Portable Harness CLI: install, project, and validate the bundle."""
import argparse
import json
import os
import shutil
import stat
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
MARKER_BEGIN_BYTES = MARKER_BEGIN.encode("ascii")
MARKER_END_BYTES = MARKER_END.encode("ascii")


class MarkerBrokenError(Exception):
    pass


class ProjectionIOError(Exception):
    """A runtime I/O fault after node-safety checks passed (design §7.1).

    Carries a ``PROJECTION_IO_ERROR`` ContractError. It is caught at the
    projection boundary (cmd_adapt / init's adapt stage) and rendered through
    emit_command_error with exit 2, honoring ``--format``. It must never be
    confused with node-layout contract errors (§8.3), which stay exit 1.
    """

    def __init__(self, display, message):
        super().__init__(message)
        self.error = validate.ContractError("PROJECTION_IO_ERROR", display, message)
        # Progress committed to disk before the fault, attached by run_adapt so
        # the error envelope can report it truthfully (design §7.1). adapt is not
        # a cross-file transaction: files already replaced stay on disk.
        self.written = []
        self.unchanged = []
        self.stale = []


def _silent_unlink(path):
    try:
        os.unlink(path)
    except OSError:
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
            if command == "init":
                sys.stdout.write(
                    "next: run the harness-bootstrap skill in your agent "
                    "to customize this Harness\n"
                )
    return 0 if ok else 1


def emit_command_error(fmt, command, errors, extra, notices=()):
    """Render a post-parse command-level error (exit 2), honoring --format.

    json → full envelope on stdout (ok:false, command, errors, notices plus the
    subcommand's documented fields). text → escaped ``[CODE] path: message``
    lines on stderr for errors then notices. ``notices`` carries non-failing
    context such as INIT_CLEANUP_HINT on post-copy failures. Always returns 2.
    """
    errors = sorted(errors)
    notices = sorted(notices)
    if fmt == "json":
        payload = {
            "ok": False,
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
            sys.stderr.write(
                f"[{validate.escape_text_field(item.code)}] "
                f"{validate.escape_text_field(item.path)}: "
                f"{validate.escape_text_field(item.message)}\n"
            )
    return 2


def _check_marker_integrity(data):
    """Raise MarkerBrokenError if managed-block markers are unpaired/reversed.

    Zero markers (a plain user or tool-owned file) is intact, not broken.
    """
    begins = data.count(MARKER_BEGIN_BYTES)
    ends = data.count(MARKER_END_BYTES)
    if begins == 0 and ends == 0:
        return
    if begins != 1 or ends != 1:
        raise MarkerBrokenError("managed block markers are broken")
    if data.index(MARKER_END_BYTES) < data.index(MARKER_BEGIN_BYTES):
        raise MarkerBrokenError("managed block markers are broken")


def apply_managed_block(existing, body):
    """Insert or refresh the managed block at the byte level.

    ``existing`` is ``bytes`` (or ``None`` for an absent file); ``body`` is the
    rendered block body as ``bytes``. User bytes outside the managed span are
    preserved verbatim (CRLF, blank lines after END, missing trailing newline,
    non-ASCII). No newline translation is applied anywhere. Returns ``bytes``.
    """
    block = MARKER_BEGIN_BYTES + b"\n" + body + b"\n" + MARKER_END_BYTES + b"\n"
    if existing is None or existing == b"":
        return block
    begins = existing.count(MARKER_BEGIN_BYTES)
    ends = existing.count(MARKER_END_BYTES)
    if begins == 0 and ends == 0:
        prefix = existing
        if prefix[-1:] != b"\n":
            prefix += b"\n"
        return prefix + b"\n" + block
    if begins != 1 or ends != 1:
        raise MarkerBrokenError("managed block markers are broken")
    begin_index = existing.index(MARKER_BEGIN_BYTES)
    end_index = existing.index(MARKER_END_BYTES)
    if end_index < begin_index:
        raise MarkerBrokenError("managed block markers are broken")
    after_end = end_index + len(MARKER_END_BYTES)
    include_following_nl = existing[after_end:after_end + 1] == b"\n"
    span_end = after_end + (1 if include_following_nl else 0)
    at_file_end = span_end == len(existing)
    if not include_following_nl and at_file_end:
        # Preserve a managed block that terminates the file with no newline.
        rendered = MARKER_BEGIN_BYTES + b"\n" + body + b"\n" + MARKER_END_BYTES
    else:
        rendered = block
    return existing[:begin_index] + rendered + existing[span_end:]


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
        return emit_command_error(
            fmt,
            "validate",
            [validate.ContractError("ROOT_UNREADABLE", ".", str(error))],
            {},
        )
    rendered = (
        validate.render_json(result) if fmt == "json" else validate.render_text(result)
    )
    sys.stdout.write(rendered)
    return 0 if result.valid else 1


def _inspect_target(project_root, rel_parts, display, errors, read):
    """Node-safety gate for one projection target (design §8.3).

    lstat every path segment from the project root to the target. Any symlink
    segment is rejected (PROJECTION_PATH_UNSAFE); the target must be absent or a
    regular file, and every intermediate segment a real directory. A FIFO,
    device, socket or directory target is rejected (PROJECTION_TARGET_INVALID)
    WITHOUT the node ever being opened.

    Returns ``("file", bytes|None)`` or ``("absent", None)`` on success, or
    ``None`` after appending a stable contract error. ``bytes`` is filled only
    when ``read`` is true and the target is a regular file.
    """
    current = project_root
    last = len(rel_parts) - 1
    for index, part in enumerate(rel_parts):
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            # This segment is absent, so the target itself is absent.
            return ("absent", None)
        except OSError as error:
            errors.append(
                validate.ContractError(
                    "PROJECTION_PATH_UNSAFE",
                    display,
                    f"projection path segment is unreadable: {error}",
                )
            )
            return None
        if stat.S_ISLNK(info.st_mode):
            errors.append(
                validate.ContractError(
                    "PROJECTION_PATH_UNSAFE",
                    display,
                    "a projection path segment is a symbolic link",
                )
            )
            return None
        if index < last:
            if not stat.S_ISDIR(info.st_mode):
                errors.append(
                    validate.ContractError(
                        "PROJECTION_TARGET_INVALID",
                        display,
                        "a projection parent path segment is not a directory",
                    )
                )
                return None
            continue
        # Final segment: only an absent path or a regular file is allowed.
        if stat.S_ISREG(info.st_mode):
            if not read:
                return ("file", None)
            try:
                return ("file", current.read_bytes())
            except OSError as error:
                # Node check passed but the read failed: a runtime I/O fault,
                # not a contract violation. Surface it as exit 2, not a bare
                # top-level INTERNAL_ERROR (design §7.1).
                raise ProjectionIOError(
                    display, f"cannot read projection target: {error}"
                )
        errors.append(
            validate.ContractError(
                "PROJECTION_TARGET_INVALID",
                display,
                "projection target exists but is not a regular file",
            )
        )
        return None
    return ("absent", None)


def _write_all(descriptor, data, display):
    """Write every byte of ``data``, tolerating short writes.

    POSIX ``os.write`` may write fewer bytes than requested; loop until all are
    committed. A return of 0 (zero progress) or an ``OSError`` is a failure.
    """
    view = memoryview(data)
    total = 0
    length = len(data)
    while total < length:
        try:
            count = os.write(descriptor, view[total:])
        except OSError as error:
            raise ProjectionIOError(display, f"failed to write projection: {error}")
        if count == 0:
            raise ProjectionIOError(display, "projection write made zero progress")
        total += count


def _write_projection(project_root, rel_parts, display, data, errors):
    """Failure-atomic projection write (design §8.3).

    Re-verify node safety, stage the bytes in a deterministically named temp
    regular file (``<name>.harness-tmp``) next to the target, fsync, re-verify
    the target node, then commit with ``os.replace``. Any failure leaves the
    original target byte-identical, removes the temp file, and keeps the target
    out of ``written``. Node-layout faults append a stable contract error and
    return False (exit 1); runtime I/O faults raise ProjectionIOError (exit 2).
    """
    if _inspect_target(project_root, rel_parts, display, errors, read=False) is None:
        return False
    target = project_root.joinpath(*rel_parts)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        errors.append(
            validate.ContractError(
                "PROJECTION_PATH_UNSAFE",
                display,
                f"cannot create projection parent directory: {error}",
            )
        )
        return False
    temp = target.with_name(target.name + ".harness-tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(temp, flags, 0o644)
    except OSError as error:
        raise ProjectionIOError(
            display, f"cannot create projection temp file: {error}"
        )
    # Everything after a successful open runs inside one boundary: any failure —
    # write, fsync, close, re-verify or replace — best-effort closes the still-open
    # descriptor, removes this temp file, and (for I/O faults) raises
    # ProjectionIOError. os.close is now INSIDE the boundary; a close failure no
    # longer escapes as a raw OSError leaving the temp node behind (design §8.3).
    committed = False
    try:
        _write_all(descriptor, data, display)
        try:
            os.fsync(descriptor)
        except OSError as error:
            raise ProjectionIOError(display, f"failed to fsync projection: {error}")
        # Descriptor ownership (design §8.3): os.close is called EXACTLY ONCE per
        # fd. descriptor is set to None BEFORE entering os.close, so whether the
        # call returns or raises, the finally clause below can never issue a
        # second close on the same fd. A raising close means the fd is CONSUMED
        # and is NEVER retried (a retry could close an fd the OS has already
        # reused, which is worse than a leak). If close raises BEFORE the real
        # release, we accept the pathological in-process fd residual — this CLI is
        # a short-lived process and the residual is reclaimed at exit (§8.3) — and
        # convert to ProjectionIOError; committed stays False so the finally still
        # removes the temp file, and the original target is byte-identical because
        # os.replace never ran.
        close_fd = descriptor
        descriptor = None
        try:
            os.close(close_fd)
        except OSError as error:
            raise ProjectionIOError(display, f"failed to close projection: {error}")
        # Re-verify the final target immediately before the atomic swap to narrow
        # the check-then-use race. A node-layout change here is an exit-1 contract
        # error, so the staged temp file is discarded and no commit happens.
        reverify = []
        if _inspect_target(project_root, rel_parts, display, reverify, read=False) is None:
            errors.extend(reverify)
            return False
        try:
            os.replace(temp, target)
        except OSError as error:
            raise ProjectionIOError(display, f"failed to commit projection: {error}")
        committed = True
        return True
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if not committed:
            _silent_unlink(temp)


def run_adapt(root, manifest, check):
    """Project the manifest into platform files. Root must already be validated."""
    project_root = root.parent
    errors, notices, written, unchanged, stale = [], [], [], [], []
    try:
        _run_adapt_loop(
            project_root, manifest, check, errors, notices, written, unchanged, stale
        )
    except ProjectionIOError as io_error:
        # Carry the files already committed to disk so the error envelope reports
        # real progress instead of an empty list (design §7.1).
        io_error.written = list(written)
        io_error.unchanged = list(unchanged)
        io_error.stale = list(stale)
        raise
    return errors, notices, written, unchanged, stale


def _run_adapt_loop(
    project_root, manifest, check, errors, notices, written, unchanged, stale
):
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
        rel_parts = rel.parts
        display = rel.as_posix()
        state = _inspect_target(project_root, rel_parts, display, errors, read=True)
        if state is None:
            continue
        _kind, existing = state
        try:
            if spec["mode"] == "file":
                if existing is not None:
                    _check_marker_integrity(existing)
                expected = render_cursor_file(manifest).encode("utf-8")
            else:
                expected = apply_managed_block(
                    existing, render_block_body(manifest).encode("utf-8")
                )
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
            if existing is not None and existing == expected:
                unchanged.append(display)
            elif _write_projection(project_root, rel_parts, display, expected, errors):
                written.append(display)


def cmd_adapt(root, check, fmt):
    try:
        result = validate.validate_harness(root)
    except validate.RootUnreadableError as error:
        return emit_command_error(
            fmt,
            "adapt",
            [validate.ContractError("ROOT_UNREADABLE", ".", str(error))],
            {"written": [], "unchanged": [], "stale": []},
        )
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
    # Post-validate manifest re-read (design §7.3). validate_harness already
    # parsed this file, but a read/decode failure between then and now is a
    # check-then-use race, not a contract violation: surface it as a command-
    # level PROJECTION_IO_ERROR (exit 2) with the full adapt envelope rather than
    # letting a bare OSError/JSONDecodeError escape to INTERNAL_ERROR.
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return emit_command_error(
            fmt,
            "adapt",
            [
                validate.ContractError(
                    "PROJECTION_IO_ERROR",
                    ".",
                    f"failed to re-read manifest after validation: {error}",
                )
            ],
            {"written": [], "unchanged": [], "stale": []},
        )
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
    try:
        errors, notices, written, unchanged, stale = run_adapt(root, manifest, check)
    except ProjectionIOError as io_error:
        return emit_command_error(
            fmt,
            "adapt",
            [io_error.error],
            {
                "written": list(io_error.written),
                "unchanged": list(io_error.unchanged),
                "stale": list(io_error.stale),
            },
        )
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


def _init_failure(fmt, errors, notices=(), target=None, projected_files=None):
    # projected_files defaults to empty (pre-copy failures commit nothing) but
    # MUST carry the real committed projections on exit-1 paths that follow a
    # partial adapt (node-layout error mid-loop, final-validation failure). An
    # empty list there is a false external fact (design §7.1).
    return emit(
        fmt,
        "init",
        False,
        errors,
        list(notices),
        {"target": target, "projected_files": list(projected_files or [])},
    )


def cmd_init(target, adapters_raw, fmt):
    source = BIN_DIR.parent
    adapters_override = None
    if adapters_raw is not None:
        argument_errors = []
        adapters_override = _parse_adapters_argument(adapters_raw, argument_errors)
        if argument_errors:
            return emit_command_error(
                fmt,
                "init",
                argument_errors,
                {"target": None, "projected_files": []},
            )

    try:
        source_result = validate.validate_harness(source)
    except validate.RootUnreadableError as error:
        return emit_command_error(
            fmt,
            "init",
            [validate.ContractError("ROOT_UNREADABLE", ".", str(error))],
            {"target": None, "projected_files": []},
        )
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

    # Source manifest re-read (design §7.2 step 3). Source validation just
    # succeeded, but a read/decode fault between then and now is a post-parse
    # runtime I/O failure, not a bare INTERNAL_ERROR: report INIT_IO_ERROR /
    # exit 2 through the envelope. The destination .harness does not exist yet
    # (copytree has not run), so there is no cleanup hint and target is null.
    try:
        source_manifest = json.loads(
            (source / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        return emit_command_error(
            fmt,
            "init",
            [
                validate.ContractError(
                    "INIT_IO_ERROR",
                    "manifest.json",
                    f"failed to re-read source manifest: {error}",
                )
            ],
            {"target": None, "projected_files": []},
        )
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
    # lexists (not exists) so ANY directory entry named .harness — regular
    # file, directory, or symlink including a dangling one — counts as
    # already existing and is refused before copytree (design §7.2 step 2).
    if os.path.lexists(destination):
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

    cleanup_hint = validate.ContractError(
        "INIT_CLEANUP_HINT",
        str(destination),
        "initialization failed after copying; remove this directory to retry",
    )
    try:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".DS_Store",
            ),
        )
    except (shutil.Error, OSError) as error:
        # Copy-stage I/O fault (bad source node, target disk failure): a
        # command-level error per §7.2 step 3. Render through the envelope with
        # exit 2; when a partial .harness was created, attach the cleanup hint.
        copy_notices = [cleanup_hint] if os.path.lexists(destination) else []
        return emit_command_error(
            fmt,
            "init",
            [
                validate.ContractError(
                    "INIT_IO_ERROR",
                    str(destination),
                    f"failed to copy template into project: {error}",
                )
            ],
            {"target": str(destination), "projected_files": []},
            notices=copy_notices,
        )

    # Read/stamp/write the copied manifest. This runs after copytree, so the
    # destination .harness is fully on disk; an I/O fault here is a command-level
    # error per §7.2 step 3, rendered like the copy stage (INIT_IO_ERROR, exit 2,
    # cleanup hint). A JSONDecodeError is effectively impossible (the source was
    # just validated) but is routed to the same code for belt-and-braces.
    try:
        manifest = json.loads(
            (destination / "manifest.json").read_text(encoding="utf-8")
        )
        manifest["origin"] = {
            "template_name": TEMPLATE_NAME,
            "template_version": source_manifest["template_version"],
            "initialized_at_schema": manifest["schema_version"],
        }
        if adapters_override is not None:
            manifest["adapters"] = adapters_override
        (destination / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError) as error:
        return emit_command_error(
            fmt,
            "init",
            [
                validate.ContractError(
                    "INIT_IO_ERROR",
                    str(destination),
                    f"failed to stamp project manifest: {error}",
                )
            ],
            {"target": str(destination), "projected_files": []},
            notices=[cleanup_hint],
        )

    try:
        errors, notices, written, unchanged, stale = run_adapt(
            destination, manifest, check=False
        )
    except ProjectionIOError as io_error:
        # Post-copy runtime I/O fault: exit 2 per §7.1, but §7.2 still requires
        # the cleanup hint so the user knows the copied tree remains on disk.
        # projected_files reports the projections committed before the fault.
        return emit_command_error(
            fmt,
            "init",
            [io_error.error],
            {
                "target": str(destination),
                "projected_files": list(io_error.written),
            },
            notices=[cleanup_hint],
        )
    if errors:
        # exit-1 contract error mid-adapt (e.g. a node-layout PROJECTION_* on a
        # later projection). run_adapt continues past node errors, so earlier and
        # later projections may already be committed: report the real progress
        # (design §7.1), never a fixed empty list.
        return _init_failure(
            fmt,
            errors,
            notices=[cleanup_hint] + notices,
            target=str(destination),
            projected_files=written + unchanged,
        )

    # Final validate reads files inside the freshly written destination; an
    # OSError there is a post-parse runtime I/O fault (design §7.2 step 3), not a
    # contract violation. Route it to INIT_IO_ERROR / exit 2 with the cleanup
    # hint and real committed projections, rather than escaping to the bare
    # INTERNAL_ERROR handler even when json was requested.
    try:
        final_result = validate.validate_harness(destination)
    except (validate.RootUnreadableError, OSError) as error:
        return emit_command_error(
            fmt,
            "init",
            [
                validate.ContractError(
                    "INIT_IO_ERROR",
                    str(destination),
                    f"failed to validate initialized harness: {error}",
                )
            ],
            {
                "target": str(destination),
                "projected_files": written + unchanged,
            },
            notices=[cleanup_hint],
        )
    if not final_result.valid:
        # Contract error (exit 1) after a full adapt: all projections committed,
        # so report them truthfully (design §7.1), not an empty list.
        return _init_failure(
            fmt,
            list(final_result.errors),
            notices=[cleanup_hint],
            target=str(destination),
            projected_files=written + unchanged,
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


def _escape_argv_field(value):
    """Single-line escape for argv-derived text (parser and pre-dispatch errors).

    Like ``validate.escape_text_field`` but also maps lone surrogate code points
    (``U+D800``–``U+DFFF``, produced by POSIX ``surrogateescape`` on non-UTF-8
    argv bytes) to ``\\uXXXX``. Writing such a surrogate raw would make stderr
    itself non-UTF-8, so it is escaped explicitly (design §7.1).
    """
    parts = []
    for char in str(value):
        code = ord(char)
        if code in validate._TEXT_ESCAPE_CODES or (
            validate._SURROGATE_FIRST <= code <= validate._SURROGATE_LAST
        ):
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(char)
    return "".join(parts)


def main(argv=None):
    # JSON stdout must always be valid UTF-8 (design §7.1). On POSIX, argv bytes
    # that are not valid UTF-8 arrive as lone surrogates via surrogateescape; a
    # JSON envelope built from them could not be encoded as UTF-8. Reject before
    # entering any subcommand: ARGUMENT_INVALID, exit 2, one escaped stderr line,
    # NO JSON envelope in this path.
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    for value in raw_argv:
        if isinstance(value, str) and validate._has_surrogate(value):
            sys.stderr.write(
                "[ARGUMENT_INVALID] .: argument contains bytes that are not "
                f"valid UTF-8: {_escape_argv_field(value)}\n"
            )
            return 2
    try:
        args = parse_args(argv)
    except ValueError as error:
        # H5: parser-level errors may interpolate input (unknown option text);
        # escape so an injected newline cannot split the single error line.
        sys.stderr.write(f"[ARGUMENT_INVALID] .: {_escape_argv_field(error)}\n")
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
