---
name: harness-bootstrap
description: Customize a freshly installed Harness into a project-specific Harness through evidence-based interviews and recorded outputs.
---

# Harness Bootstrap

## When to use

Run once after `harness.py init` installs this Harness into a project, or whenever project-level customization must be rebuilt.

## Inputs

- The target project's codebase.
- The installed Harness directory.
- A human partner able to approve project decisions.

## Non-negotiable interview rules

1. **Scout before asking.** First read the codebase: languages, build and test commands, directory layout, lint and CI configuration, existing agent instruction files. Never ask the user anything the codebase can answer.
2. **One question per message.**
3. **Every question offers 2-4 enumerated options.** Open questions must present drafted candidates based on scouting, for confirmation or edit.
4. **Every question marks a recommended option**, with a reason grounded in scouting evidence.
5. **Every option states its trade-off**, not only its benefit.
6. **The default path must work.** A user who accepts every recommendation must end with a coherent, usable Harness.

### Example - compliant

> Which command set is the delivery quality gate? I found `pytest` in CI and a `lint` script in the build file.
>
> - A. `pytest` only - fastest gate, but style drift goes uncaught. (recommended: CI already enforces it)
> - B. `pytest` plus `lint` - stricter, slower on large changes.
> - C. Other - tell me the exact commands. (requires you to specify and maintain them manually)

### Example - violations

> "What are your coding standards?" (transfers discovery cost to the user)
>
> "Anything else to add?" (no options, no recommendation)

## Steps

1. Scout the codebase and record findings.
2. Interview the user following the rules above. Cover at least: one-line project purpose, delivery quality-gate commands, change approval convention, Harness prose language.
3. Write project rules into `rules/` (for example `rules/project.md`) and register each new file in `manifest.json` under `components`.
4. Draft `wiki/overview.md` and `wiki/conventions.md` skeletons from scouting findings, marking gaps explicitly.
5. Record this bootstrap itself as the first Change Record using the change-delivery skill.
6. Write the customization record described below into the same Change Record directory.

## Customization record

Write a file named `customization-record.md` inside the bootstrap Change Record directory, alongside `summary.md`, `spec.md`, and `tasks.md`. Extra files in a Change Record are permitted by the contract, so this file lives beside them without special registration.

The file must contain a table with one row per template asset the bootstrap touched. Use exactly these columns:

| Asset | Action | Reason | Reusability guess |
| ----- | ------ | ------ | ----------------- |

- **Asset** - the bundle-relative path of the touched template asset.
- **Action** - one of `modified`, `replaced`, `added`, or `removed`.
- **Reason** - one sentence, grounded in scouting or interview evidence, explaining why the asset was touched.
- **Reusability guess** - one of `generic`, `stack`, or `project`. `generic` means the change would apply to any project. `stack` means it applies to any project on the same technology stack. `project` means it is specific to this project's domain.

Close the file with a line stating that rows marked `stack` or `generic` are candidate evidence for upstream template layering and should be preserved verbatim when the record is later shared upstream.

This customization record is not part of the machine contract; the validator does not parse it.

## Outputs

- Project rules registered in the manifest.
- Wiki skeleton under `wiki/`.
- A complete first Change Record.
- A customization record (`customization-record.md`) inside the bootstrap Change Record directory.

## Verification

Run `python3 .harness/bin/harness.py validate` and `python3 .harness/bin/harness.py adapt --check` from the project root; store the exact output in the Change Record summary.
