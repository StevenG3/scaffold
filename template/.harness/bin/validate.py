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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Validate a portable Harness contract.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def render_text(result):
    if result.valid:
        return "Harness contract is valid.\n"
    return "".join(
        f"[{item.code}] {item.path}: {item.message}\n"
        for item in sorted(result.errors)
    )


def render_json(result):
    payload = {
        "valid": result.valid,
        "errors": [asdict(item) for item in sorted(result.errors)],
        "root": str(result.root),
        "schema_version": result.schema_version,
    }
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

    reject_unknown_fields(manifest, TOP_LEVEL_FIELDS, (), errors)

    schema_version = require_field(manifest, "schema_version", int, (), errors)
    if schema_version is not None and schema_version != 1:
        errors.append(
            ContractError(
                "SCHEMA_VERSION_UNSUPPORTED",
                json_pointer("schema_version"),
                f"schema_version {schema_version!r} is unsupported",
            )
        )

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
            if kind is not None and kind not in BUILTIN_KINDS and not kind.startswith("x-"):
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


def _is_within_root(root, path):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_safe_path(root, declared, *, expect, pointer, errors):
    """Validate Manifest path syntax and filesystem target.

    Syntax/traversal errors use JSON Pointer. Filesystem errors use the
    declared POSIX relative path. Returns the resolved Path on success,
    otherwise None.
    """
    if "\\" in declared or re.match(r"^[A-Za-z]:", declared):
        errors.append(
            ContractError(
                "PATH_SYNTAX_INVALID",
                pointer,
                "path must use POSIX separators without Windows drive prefixes",
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

    display_path = pure.as_posix()
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        errors.append(
            ContractError(
                "PATH_MISSING",
                display_path,
                "referenced path does not exist",
            )
        )
        return None
    except OSError as error:
        errors.append(
            ContractError(
                "PATH_MISSING",
                display_path,
                f"referenced path is unreadable: {error}",
            )
        )
        return None

    if not _is_within_root(root, resolved):
        errors.append(
            ContractError(
                "PATH_ESCAPE",
                display_path,
                "resolved path escapes the Harness root",
            )
        )
        return None

    if expect == "file":
        if not resolved.is_file() or resolved.is_symlink():
            # is_file follows symlinks; after resolve, symlink targets are regular paths.
            # Use the resolved node type.
            pass
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
        # If empty, still return path? Frontmatter should not run on empty.
        # Check if FILE_EMPTY was just added - validate_nonempty_file appends.
        # Caller should check: only apply frontmatter if file non-empty.
        # Return resolved even if empty so caller can inspect; or return None if empty.
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
            if (
                resolved is not None
                and type(kind) is str
                and kind == "skill"
            ):
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


def validate_harness(root):
    root = Path(root).resolve()
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
        manifest = json.loads(text)
    except json.JSONDecodeError as error:
        errors.append(
            ContractError(
                "MANIFEST_JSON_INVALID",
                "manifest.json",
                f"invalid JSON at line {error.lineno} column {error.colno}",
            )
        )
        return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))

    if type(manifest) is dict and "schema_version" in manifest:
        schema_version = manifest.get("schema_version")

    errors.extend(validate_manifest_structure(manifest))
    validate_manifest_paths(root, manifest, errors)
    return ValidationResult(root=root, schema_version=schema_version, errors=tuple(errors))


def main(argv=None):
    args = parse_args(argv)
    result = validate_harness(args.root)
    rendered = render_json(result) if args.format == "json" else render_text(result)
    sys.stdout.write(rendered)
    return 0 if result.valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as error:
        sys.stderr.write(f"[INTERNAL_ERROR] .: {error}\n")
        raise SystemExit(2)
