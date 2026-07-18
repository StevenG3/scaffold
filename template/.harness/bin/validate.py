#!/usr/bin/env python3
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


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
    schema_version = manifest.get("schema_version") if isinstance(manifest, dict) else None
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
