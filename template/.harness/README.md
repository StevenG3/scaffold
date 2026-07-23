# Portable AI Coding Harness

This directory is a self-contained, project-neutral Harness. Teams may translate or replace its prose while preserving `manifest.json` and the declared file contract.

## Install into a project

From a local copy of the template, run:

    python3 <template>/.harness/bin/harness.py init --target <project-dir>

`init` copies the bundle, stamps its origin, generates platform projection files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/harness.mdc`), and validates the result. Then open your agent and run the `harness-bootstrap` skill to customize the Harness for the project.

## Start (installed projects)

1. Read `manifest.json`.
2. Load only components needed for the current task.
3. Create a Change Record from `templates/change/` before implementation.
4. Record verification evidence in the Change Record.
5. Run `python3 bin/harness.py validate` before delivery.

## Components

- `agents/`: replaceable role definitions.
- `rules/`: stable project constraints.
- `skills/`: reusable workflows, including `harness-bootstrap` for first-time customization.
- `templates/change/`: required Change Record shape.
- `changes/`: project-local delivery history.
- `wiki/`: project knowledge base (not part of the machine contract).

## Commands

- `python3 bin/harness.py validate` - check the Harness contract (read-only).
- `python3 bin/harness.py adapt` - regenerate platform projection files; only managed blocks are touched.
- `python3 bin/harness.py adapt --check` - fail if projections are stale; useful in CI.

All commands require Python 3.9 or newer and use only the standard library.
