---
name: change-delivery
description: Deliver a repository change through an explicit record, scoped execution, and reproducible verification.
---

# Change Delivery

## When to use

Use for any repository change that must be reviewed or audited.

## Inputs

- Requested outcome and constraints.
- Project-specific rules and context.
- Verification commands available in the target repository.

## Steps

1. Copy `templates/change/` into a new directory under `changes/`.
2. Complete `spec.md` and obtain project-required approval.
3. Break work into verifiable items in `tasks.md`.
4. Execute only approved scope.
5. Run declared checks and record exact evidence in `summary.md`.

## Outputs

- Complete Change Record.
- Scoped repository change.
- Reproducible verification evidence.

## Verification

Run `python3 bin/validate.py` and the target repository's own quality gates.
