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

### Scope

The record covers **every Harness asset the bootstrap touched**, with no exemptions. One row per asset, including all of:

- new files written under `rules/`;
- new pages written under `wiki/`;
- every component registration change in `manifest.json` (one row per component);
- every change to a file that shipped with the installed bundle, such as the README, pre-existing rules, skills, and templates.

An asset that was touched but is hard to classify still gets a row; it is never omitted.

### Columns

The file must contain a table using exactly these columns:

| Asset | Action | Reason | Reusability guess |
| ----- | ------ | ------ | ----------------- |

- **Asset** - the bundle-relative path of the touched asset. For a manifest component registration, write the manifest path followed by the component id in parentheses.
- **Action** - exactly one of `added`, `modified`, `replaced`, or `removed`, per the definitions below.
- **Reason** - one sentence, grounded in scouting or interview evidence, explaining why the asset was touched.
- **Reusability guess** - one of `generic`, `stack`, or `project`. `generic` means the change would apply to any project. `stack` means it applies to any project on the same technology stack. `project` means it is specific to this project's domain.

### Action definitions

The four values are mutually exclusive; exactly one applies to any asset.

- `added` - the asset did not exist in the installed bundle; bootstrap created it. This includes a new manifest component registration, recorded as the action of that manifest row.
- `modified` - the asset existed and retains part of its original content after the change.
- `replaced` - the asset existed and none of its original prose remains (wholesale rewrite).
- `removed` - the asset existed and was deleted, or its manifest component was deregistered.

### Evidence carrier

The table is an index, not the evidence itself. The rewritten content must stay recoverable, by exactly one of these carriers, decided in this order:

1. **If the project uses version control**, every asset change made by the bootstrap must land in a referenceable commit, and `summary.md` must record that commit id. The diff is the evidence; no copies are made.
2. **Otherwise**, before writing, bootstrap must copy the original of every asset it will mark `modified`, `replaced`, or `removed` into an `originals/` subdirectory of this Change Record directory, preserving the asset's bundle-relative path. Those copies are the evidence, and `summary.md` must say that `originals/` is the carrier because no version control is in use.

### Worked example

| Asset | Action | Reason | Reusability guess |
| ----- | ------ | ------ | ----------------- |
| `rules/project.md` | `added` | The interview settled the delivery quality gate and the change approval convention, which had no home in the shipped rules. | `project` |
| `manifest.json` (`rules/project.md`) | `added` | The new project rules file must be a registered component for the validator to see it. | `project` |
| `README.md` | `modified` | Replaced the placeholder project name and gate commands with the scouted ones; the surrounding structure and guidance are unchanged. | `generic` |
| `wiki/README.md` | `replaced` | The shipped placeholder text was rewritten end to end into an index of this project's actual wiki pages and domain notes. | `project` |
| `rules/delivery.md` | `modified` | Added the reviewer approval the user requires before merge; the four delivery states and the rest of the shipped rule stand. | `generic` |
| `wiki/conventions.md` | `added` | Scouting found build, test, and lint conventions that come from the project's technology stack rather than its domain. | `stack` |

Example evidence sentence for `summary.md`, version-control case:

> All bootstrap asset changes are in commit `a1b2c3d`; see its diff for the exact rewritten content.

Example evidence sentence for `summary.md`, no version control:

> This project has no version control, so the pre-bootstrap originals of every `modified`, `replaced`, and `removed` asset are stored under `originals/` in this Change Record directory.

Close the file with a line stating that rows marked `stack` or `generic` are candidate evidence for upstream template layering and should be preserved verbatim when the record is later shared upstream.

This customization record is not part of the machine contract; the validator does not parse it.

## Outputs

- Project rules registered in the manifest.
- Wiki skeleton under `wiki/`.
- A complete first Change Record.
- A customization record (`customization-record.md`) inside the bootstrap Change Record directory.

## Verification

Run `python3 .harness/bin/harness.py validate` and `python3 .harness/bin/harness.py adapt --check` from the project root; store the exact output in the Change Record summary.
