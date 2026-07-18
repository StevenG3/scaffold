# Portable AI Coding Harness

This directory is a self-contained, project-neutral Harness. Teams may translate or replace its prose while preserving `manifest.json` and the declared file contract.

## Start

1. Read `manifest.json`.
2. Load only components needed for the current task.
3. Create a Change Record from `templates/change/` before implementation.
4. Record verification evidence in the Change Record.
5. Run `python3 bin/validate.py` before delivery.

## Components

- `agents/`: replaceable role definitions.
- `rules/`: stable project constraints.
- `skills/`: reusable workflows.
- `templates/change/`: required Change Record shape.
- `changes/`: project-local delivery history.

## Validation

Run `python3 bin/validate.py`. The validator is read-only and requires Python 3.9 or newer.
