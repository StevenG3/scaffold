#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

BUILTIN_KINDS = {"agent", "rule", "skill"}
TOP_LEVEL_FIELDS = {"schema_version", "entrypoint", "components", "change_management"}
COMPONENT_FIELDS = {"id", "kind", "path"}
CHANGE_FIELDS = {"template", "records", "required_files"}
SUPPORTED_SCHEMA_VERSIONS = (1, 2)
BUILTIN_ADAPTER_NAMES = ("claude-code", "codex", "cursor")
TOP_LEVEL_FIELDS_V2 = TOP_LEVEL_FIELDS | {"template_version", "adapters", "origin"}
ORIGIN_FIELDS = {"template_name", "template_version", "initialized_at_schema"}
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, order=True)
class ContractError:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    root: Path
    schema_version: object
    errors: tuple

    @property
    def valid(self):
        return not self.errors


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


class RootUnreadableError(Exception):
    pass


def parse_args(argv=None):
    parser = _ArgumentParser(description="Validate a portable Harness contract.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


_TEXT_ESCAPE_CODES = frozenset(
    {0x7F, 0x85, 0x2028, 0x2029} | set(range(0x20))
)

_SURROGATE_FIRST = 0xD800
_SURROGATE_LAST = 0xDFFF


def _has_surrogate(text):
    return any(_SURROGATE_FIRST <= ord(char) <= _SURROGATE_LAST for char in text)


def contains_unpaired_surrogate(value):
    """Report whether decoded JSON still holds a surrogate code unit.

    ``json.loads`` combines a valid ``\\uD800``-``\\uDC00`` style pair into
    one Unicode scalar, so anything still in ``U+D800``-``U+DFFF`` was
    unpaired in the source. Such a string cannot be encoded as UTF-8, which
    would otherwise surface as an ``INTERNAL_ERROR`` at render time instead
    of a Manifest contract error.

    Walks an explicit stack so deep nesting cannot raise ``RecursionError``.
    """
    stack = [value]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            if _has_surrogate(node):
                return True
        elif isinstance(node, dict):
            for key, item in node.items():
                if isinstance(key, str) and _has_surrogate(key):
                    return True
                stack.append(item)
        elif isinstance(node, list):
            stack.extend(node)
    return False


def escape_text_field(value):
    """Escape line-breaking and C0 controls for single-line Text output.

    Printable Unicode is unchanged. Deterministic form: ``\\uXXXX`` for
    ``U+0000``–``U+001F``, ``U+007F`` (DEL), ``U+0085`` (NEL),
    ``U+2028`` (Line Separator), ``U+2029`` (Paragraph Separator) and every
    surrogate code point ``U+D800``–``U+DFFF``. Surrogates arrive from POSIX
    ``surrogateescape`` over non-UTF-8 filesystem names (e.g. a Change Record
    directory named with byte ``0xff`` yields ``U+DCFF`` in the reported
    path); rendering them raw would emit an illegal byte on stdout. Escaping
    to ``\\uXXXX`` keeps Text output pure ASCII and strictly valid UTF-8 while
    identifying the original code unit. Surrogate-free values are unchanged.
    """
    parts = []
    for char in str(value):
        code = ord(char)
        if code in _TEXT_ESCAPE_CODES or _SURROGATE_FIRST <= code <= _SURROGATE_LAST:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(char)
    return "".join(parts)


def _escape_surrogates(text):
    """Deterministic ASCII escape of surrogate code points in ``text``.

    Only ``U+D800``–``U+DFFF`` are rewritten (to ``\\uXXXX``); every other
    character — including legitimate non-ASCII scalars — is returned verbatim,
    so any surrogate-free string is byte-identical to its input.
    """
    if not _has_surrogate(text):
        return text
    parts = []
    for char in text:
        code = ord(char)
        if _SURROGATE_FIRST <= code <= _SURROGATE_LAST:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(char)
    return "".join(parts)


def _sanitize_json_strings(value):
    """Recursively escape surrogate code points at the JSON string egress.

    ``render_json`` uses ``ensure_ascii=False`` so normal non-ASCII text stays
    raw UTF-8. A lone surrogate cannot encode as UTF-8, so it is escaped here
    (in both keys and values) before serialization. Surrogate-free payloads
    are structurally identical, keeping non-surrogate output byte-for-byte
    unchanged.
    """
    if isinstance(value, str):
        return _escape_surrogates(value)
    if isinstance(value, dict):
        return {
            (_escape_surrogates(key) if isinstance(key, str) else key):
                _sanitize_json_strings(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_json_strings(item) for item in value]
    return value


def render_text(result):
    if result.valid:
        return "Harness contract is valid.\n"
    return "".join(
        (
            f"[{escape_text_field(item.code)}] "
            f"{escape_text_field(item.path)}: "
            f"{escape_text_field(item.message)}\n"
        )
        for item in sorted(result.errors)
    )


def render_json(result):
    payload = {
        "valid": result.valid,
        "errors": [asdict(item) for item in sorted(result.errors)],
        "root": str(result.root),
        "schema_version": result.schema_version,
    }
    # Escape surrogate code points at the string egress so the emitted bytes are
    # always strictly valid UTF-8 (§7.4 ruling). ensure_ascii stays False, so
    # legitimate non-ASCII scalars remain raw UTF-8 and surrogate-free results
    # are byte-identical to prior v0 output.
    payload = _sanitize_json_strings(payload)
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def json_pointer(*parts):
    escaped = []
    for part in parts:
        text = str(part)
        text = text.replace("~", "~0").replace("/", "~1")
        escaped.append(text)
    return "manifest.json#/" + "/".join(escaped)


def reject_unknown_fields(value, allowed, location, errors):
    if type(value) is not dict:
        return
    for key in value:
        if key in allowed or (isinstance(key, str) and key.startswith("x-")):
            continue
        pointer = json_pointer(*location, key) if location else json_pointer(key)
        errors.append(
            ContractError(
                "FIELD_UNKNOWN",
                pointer,
                f"unknown field {key!r}",
            )
        )


def require_field(value, field, expected_type, location, errors):
    pointer = json_pointer(*location, field) if location else json_pointer(field)
    if type(value) is not dict or field not in value:
        errors.append(
            ContractError(
                "FIELD_MISSING",
                pointer,
                f"required field {field!r} is missing",
            )
        )
        return None
    actual = value[field]
    if type(actual) is not expected_type:
        errors.append(
            ContractError(
                "FIELD_TYPE_INVALID",
                pointer,
                f"field {field!r} must be {expected_type.__name__}",
            )
        )
        return None
    if expected_type is str and actual == "":
        errors.append(
            ContractError(
                "FIELD_TYPE_INVALID",
                pointer,
                f"field {field!r} must be a non-empty string",
            )
        )
        return None
    if expected_type is list and len(actual) == 0:
        errors.append(
            ContractError(
                "FIELD_TYPE_INVALID",
                pointer,
                f"field {field!r} must be a non-empty list",
            )
        )
        return None
    return actual


def validate_manifest_structure(manifest):
    errors = []
    if type(manifest) is not dict:
        errors.append(
            ContractError(
                "FIELD_TYPE_INVALID",
                "manifest.json#/",
                "manifest root must be an object",
            )
        )
        return errors

    schema_version = require_field(manifest, "schema_version", int, (), errors)
    if schema_version is not None and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            ContractError(
                "SCHEMA_VERSION_UNSUPPORTED",
                json_pointer("schema_version"),
                f"schema_version {schema_version!r} is unsupported",
            )
        )

    allowed_top = TOP_LEVEL_FIELDS_V2 if schema_version == 2 else TOP_LEVEL_FIELDS
    reject_unknown_fields(manifest, allowed_top, (), errors)
    if schema_version == 2:
        _validate_v2_fields(manifest, errors)

    require_field(manifest, "entrypoint", str, (), errors)

    components = require_field(manifest, "components", list, (), errors)
    seen_ids = {}
    if components is not None:
        for index, component in enumerate(components):
            location = ("components", index)
            if type(component) is not dict:
                errors.append(
                    ContractError(
                        "FIELD_TYPE_INVALID",
                        json_pointer(*location),
                        "component must be an object",
                    )
                )
                continue
            reject_unknown_fields(component, COMPONENT_FIELDS, location, errors)
            component_id = require_field(component, "id", str, location, errors)
            kind = require_field(component, "kind", str, location, errors)
            require_field(component, "path", str, location, errors)
            if component_id is not None:
                if component_id in seen_ids:
                    errors.append(
                        ContractError(
                            "COMPONENT_ID_DUPLICATE",
                            json_pointer(*location, "id"),
                            f"duplicate component id {component_id!r}",
                        )
                    )
                else:
                    seen_ids[component_id] = index
            if kind is not None and not _is_supported_kind(kind):
                errors.append(
                    ContractError(
                        "COMPONENT_KIND_UNSUPPORTED",
                        json_pointer(*location, "kind"),
                        f"unsupported component kind {kind!r}",
                    )
                )

    change = require_field(manifest, "change_management", dict, (), errors)
    if change is not None:
        location = ("change_management",)
        reject_unknown_fields(change, CHANGE_FIELDS, location, errors)
        require_field(change, "template", str, location, errors)
        require_field(change, "records", str, location, errors)
        required_files = require_field(change, "required_files", list, location, errors)
        if required_files is not None:
            seen_files = set()
            invalid = False
            for index, item in enumerate(required_files):
                item_pointer = json_pointer("change_management", "required_files", index)
                if type(item) is not str or item == "":
                    errors.append(
                        ContractError(
                            "FIELD_TYPE_INVALID",
                            item_pointer,
                            "required file path must be a non-empty string",
                        )
                    )
                    invalid = True
                    continue
                if item in seen_files:
                    invalid = True
                seen_files.add(item)
            if invalid or len(seen_files) != len(required_files):
                # Plan requires empty or duplicate required_files → FIELD_TYPE_INVALID
                # at the required_files field path.
                if len(required_files) == 0 or len(seen_files) != len(required_files):
                    # Avoid duplicate error when empty list already reported by require_field.
                    if len(required_files) != 0 and len(seen_files) != len(required_files):
                        errors.append(
                            ContractError(
                                "FIELD_TYPE_INVALID",
                                json_pointer("change_management", "required_files"),
                                "required_files must not contain duplicates",
                            )
                        )

    return errors


def _validate_semver(value, pointer, errors, field_name):
    if type(value) is not str or not _SEMVER_RE.match(value):
        errors.append(
            ContractError(
                "FIELD_VALUE_INVALID",
                pointer,
                f"field {field_name!r} must be a semantic version like '1.2.3'",
            )
        )
        return False
    return True


def _validate_v2_fields(manifest, errors):
    if "template_version" in manifest:
        _validate_semver(
            manifest["template_version"],
            json_pointer("template_version"),
            errors,
            "template_version",
        )

    if "adapters" in manifest:
        adapters = manifest["adapters"]
        if type(adapters) is not list:
            errors.append(
                ContractError(
                    "FIELD_TYPE_INVALID",
                    json_pointer("adapters"),
                    "field 'adapters' must be list",
                )
            )
        else:
            seen = set()
            for index, name in enumerate(adapters):
                pointer = json_pointer("adapters", index)
                if type(name) is not str or name == "":
                    errors.append(
                        ContractError(
                            "FIELD_TYPE_INVALID",
                            pointer,
                            "adapter name must be a non-empty string",
                        )
                    )
                    continue
                if name not in BUILTIN_ADAPTER_NAMES and not (
                    name.startswith("x-") and len(name) > 2
                ):
                    errors.append(
                        ContractError(
                            "FIELD_VALUE_INVALID",
                            pointer,
                            f"unsupported adapter {name!r}",
                        )
                    )
                if name in seen:
                    errors.append(
                        ContractError(
                            "FIELD_VALUE_INVALID",
                            pointer,
                            f"duplicate adapter {name!r}",
                        )
                    )
                seen.add(name)

    origin = manifest.get("origin")
    if "origin" in manifest and origin is not None:
        location = ("origin",)
        if type(origin) is not dict:
            errors.append(
                ContractError(
                    "FIELD_TYPE_INVALID",
                    json_pointer("origin"),
                    "field 'origin' must be null or an object",
                )
            )
        else:
            reject_unknown_fields(origin, ORIGIN_FIELDS, location, errors)
            require_field(origin, "template_name", str, location, errors)
            version = require_field(origin, "template_version", str, location, errors)
            if version is not None:
                _validate_semver(
                    version,
                    json_pointer("origin", "template_version"),
                    errors,
                    "template_version",
                )
            initialized = require_field(
                origin, "initialized_at_schema", int, location, errors
            )
            if initialized is not None and initialized not in SUPPORTED_SCHEMA_VERSIONS:
                errors.append(
                    ContractError(
                        "FIELD_VALUE_INVALID",
                        json_pointer("origin", "initialized_at_schema"),
                        f"initialized_at_schema {initialized!r} is unsupported",
                    )
                )


def _is_supported_kind(kind):
    if kind in BUILTIN_KINDS:
        return True
    # Extension kinds must be "x-" plus at least one character.
    return kind.startswith("x-") and len(kind) > 2


def validate_nonempty_file(path, display_path, errors):
    if not path.read_bytes():
        errors.append(
            ContractError("FILE_EMPTY", display_path, "referenced file is empty")
        )


def validate_skill_frontmatter(path, display_path, errors):
    lines = path.read_text(encoding="utf-8").splitlines()
    invalid = ContractError(
        "SKILL_FRONTMATTER_INVALID",
        display_path,
        "skill frontmatter must start and end with --- and declare non-empty name and description",
    )
    if not lines or lines[0] != "---":
        errors.append(invalid)
        return
    closing = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            closing = index
            break
    if closing is None:
        errors.append(invalid)
        return
    has_name = False
    has_description = False
    for line in lines[1:closing]:
        if line.startswith("name:"):
            if line[5:].strip():
                has_name = True
        elif line.startswith("description:"):
            if line[12:].strip():
                has_description = True
    if not has_name or not has_description:
        errors.append(invalid)


def _is_within(base, path):
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def parse_relative_posix_path(declared, pointer, errors):
    """Shared Manifest path syntax checks. Returns PurePosixPath or None."""
    if "\0" in declared or "\\" in declared or re.match(r"^[A-Za-z]:", declared):
        errors.append(
            ContractError(
                "PATH_SYNTAX_INVALID",
                pointer,
                "path must use POSIX separators without NUL or Windows drive prefixes",
            )
        )
        return None

    pure = PurePosixPath(declared)
    if pure.is_absolute():
        errors.append(
            ContractError(
                "PATH_ABSOLUTE",
                pointer,
                "path must be relative to the Harness root",
            )
        )
        return None
    if ".." in pure.parts:
        errors.append(
            ContractError(
                "PATH_TRAVERSAL",
                pointer,
                "path must not contain '..' segments",
            )
        )
        return None
    return pure


def resolve_declared_path(
    root,
    declared,
    *,
    expect,
    pointer,
    errors,
    bases=None,
    missing_code="PATH_MISSING",
    display_path=None,
):
    """Shared safe-path helper for syntax, resolve, containment and node type.

    Syntax/absolute/traversal errors use JSON Pointer. Filesystem errors use
    display_path (default: declared POSIX path). Returns resolved Path or None.
    """
    pure = parse_relative_posix_path(declared, pointer, errors)
    if pure is None:
        return None

    if display_path is None:
        display_path = pure.as_posix()

    allowed_bases = [root]
    if bases:
        for base in bases:
            if base not in allowed_bases:
                allowed_bases.append(base)
        join_root = bases[-1]
    else:
        join_root = root

    candidate = join_root.joinpath(*pure.parts)

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        message = (
            "required change file does not exist"
            if missing_code == "CHANGE_REQUIRED_FILE_MISSING"
            else "referenced path does not exist"
        )
        errors.append(ContractError(missing_code, display_path, message))
        return None
    except OSError as error:
        message = (
            f"required change file is unreadable: {error}"
            if missing_code == "CHANGE_REQUIRED_FILE_MISSING"
            else f"referenced path is unreadable: {error}"
        )
        errors.append(ContractError(missing_code, display_path, message))
        return None
    except ValueError:
        errors.append(
            ContractError(
                "PATH_SYNTAX_INVALID",
                pointer,
                "path must use POSIX separators without NUL or Windows drive prefixes",
            )
        )
        return None

    for base in allowed_bases:
        if not _is_within(base, resolved):
            errors.append(
                ContractError(
                    "PATH_ESCAPE",
                    display_path,
                    "resolved path escapes the Harness root",
                )
            )
            return None

    if expect == "file":
        if not resolved.is_file():
            errors.append(
                ContractError(
                    "PATH_TYPE_INVALID",
                    display_path,
                    "referenced path must be a regular file",
                )
            )
            return None
        validate_nonempty_file(resolved, display_path, errors)
        if not resolved.read_bytes():
            return None
        return resolved

    if expect == "directory":
        if not resolved.is_dir():
            errors.append(
                ContractError(
                    "PATH_TYPE_INVALID",
                    display_path,
                    "referenced path must be a directory",
                )
            )
            return None
        return resolved

    raise RuntimeError(f"unsupported expect value: {expect!r}")


def resolve_safe_path(root, declared, *, expect, pointer, errors):
    return resolve_declared_path(
        root,
        declared,
        expect=expect,
        pointer=pointer,
        errors=errors,
    )


def validate_manifest_paths(root, manifest, errors):
    if type(manifest) is not dict:
        return

    entrypoint = manifest.get("entrypoint")
    if type(entrypoint) is str and entrypoint != "":
        resolve_safe_path(
            root,
            entrypoint,
            expect="file",
            pointer=json_pointer("entrypoint"),
            errors=errors,
        )

    components = manifest.get("components")
    if type(components) is list:
        for index, component in enumerate(components):
            if type(component) is not dict:
                continue
            declared = component.get("path")
            if type(declared) is not str or declared == "":
                continue
            resolved = resolve_safe_path(
                root,
                declared,
                expect="file",
                pointer=json_pointer("components", index, "path"),
                errors=errors,
            )
            kind = component.get("kind")
            if resolved is not None and type(kind) is str and kind == "skill":
                validate_skill_frontmatter(
                    resolved,
                    PurePosixPath(declared).as_posix(),
                    errors,
                )

    change = manifest.get("change_management")
    if type(change) is dict:
        template = change.get("template")
        if type(template) is str and template != "":
            resolve_safe_path(
                root,
                template,
                expect="directory",
                pointer=json_pointer("change_management", "template"),
                errors=errors,
            )
        records = change.get("records")
        if type(records) is str and records != "":
            resolve_safe_path(
                root,
                records,
                expect="directory",
                pointer=json_pointer("change_management", "records"),
                errors=errors,
            )


def validate_change_management(root, config, errors):
    if type(config) is not dict:
        return
    template_declared = config.get("template")
    records_declared = config.get("records")
    required_files = config.get("required_files")
    if type(required_files) is not list or len(required_files) == 0:
        return
    if type(template_declared) is not str or template_declared == "":
        return
    if type(records_declared) is not str or records_declared == "":
        return

    # Reuse the shared helper without duplicating syntax checks when dirs are
    # already invalid; silent probe keeps Change validation from double-reporting.
    probe_errors = []
    template_dir = resolve_declared_path(
        root,
        template_declared,
        expect="directory",
        pointer=json_pointer("change_management", "template"),
        errors=probe_errors,
    )
    records_dir = resolve_declared_path(
        root,
        records_declared,
        expect="directory",
        pointer=json_pointer("change_management", "records"),
        errors=probe_errors,
    )
    if template_dir is None or records_dir is None:
        return

    template_prefix = PurePosixPath(template_declared).as_posix()
    parsed_required = []
    for index, item in enumerate(required_files):
        if type(item) is not str or item == "":
            continue
        pointer = json_pointer("change_management", "required_files", index)
        rel_pure = parse_relative_posix_path(item, pointer, errors)
        if rel_pure is None:
            continue
        parsed_required.append(rel_pure)
        display = f"{template_prefix}/{rel_pure.as_posix()}"
        resolve_declared_path(
            root,
            rel_pure.as_posix(),
            expect="file",
            pointer=pointer,
            errors=errors,
            bases=[root, template_dir],
            missing_code="CHANGE_REQUIRED_FILE_MISSING",
            display_path=display,
        )

    for child in sorted(records_dir.iterdir(), key=lambda path: path.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        try:
            record_dir = child.resolve()
        except (OSError, ValueError):
            continue
        record_prefix = f"{PurePosixPath(records_declared).as_posix()}/{child.name}"
        for rel_pure in parsed_required:
            display = f"{record_prefix}/{rel_pure.as_posix()}"
            resolve_declared_path(
                root,
                rel_pure.as_posix(),
                expect="file",
                pointer=json_pointer("change_management", "required_files"),
                errors=errors,
                bases=[root, record_dir],
                missing_code="CHANGE_REQUIRED_FILE_MISSING",
                display_path=display,
            )


def validate_harness(root):
    root_input = Path(root)
    try:
        if not root_input.exists() or not root_input.is_dir():
            raise RootUnreadableError("harness root is missing or not a directory")
        # Probe readability before resolving content.
        next(root_input.iterdir(), None)
        root = root_input.resolve(strict=True)
    except RootUnreadableError:
        raise
    except OSError as error:
        raise RootUnreadableError(str(error)) from error

    if not root.is_dir():
        raise RootUnreadableError("harness root is missing or not a directory")

    errors = []
    schema_version = None
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append(
            ContractError(
                "MANIFEST_MISSING",
                "manifest.json",
                "manifest file does not exist",
            )
        )
        return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))
    try:
        text = manifest_path.read_text(encoding="utf-8")

        def reject_nonfinite(token):
            raise json.JSONDecodeError(
                f"non-finite constant {token!r} is not allowed",
                text,
                0,
            )

        manifest = json.loads(text, parse_constant=reject_nonfinite)
    except json.JSONDecodeError as error:
        errors.append(
            ContractError(
                "MANIFEST_JSON_INVALID",
                "manifest.json",
                f"invalid JSON at line {error.lineno} column {error.colno}",
            )
        )
        return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))

    if contains_unpaired_surrogate(manifest):
        errors.append(
            ContractError(
                "MANIFEST_JSON_INVALID",
                "manifest.json",
                "invalid JSON: unpaired surrogate code unit is not valid UTF-8",
            )
        )
        return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))

    if type(manifest) is dict and "schema_version" in manifest:
        schema_version = manifest.get("schema_version")

    errors.extend(validate_manifest_structure(manifest))
    validate_manifest_paths(root, manifest, errors)
    if type(manifest) is dict:
        validate_change_management(root, manifest.get("change_management"), errors)
    return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))


def main(argv=None):
    try:
        args = parse_args(argv)
    except ValueError as error:
        sys.stderr.write(f"[ARGUMENT_INVALID] .: {error}\n")
        return 2
    try:
        result = validate_harness(args.root)
    except RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    rendered = render_json(result) if args.format == "json" else render_text(result)
    sys.stdout.write(rendered)
    return 0 if result.valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as error:
        sys.stderr.write(f"[INTERNAL_ERROR] .: {error}\n")
        raise SystemExit(2)
