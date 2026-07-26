<!-- BEGIN HARNESS MANAGED BLOCK (harness adapt) -->
This project uses a portable AI coding harness stored in `.harness/`.

- Entrypoint: `.harness/README.md`
- Manifest: `.harness/manifest.json`

Components:

- coordinator (agent): `.harness/agents/coordinator.md`
- delivery-rule (rule): `.harness/rules/delivery.md`
- change-delivery (skill): `.harness/skills/change-delivery/SKILL.md`
- harness-bootstrap (skill): `.harness/skills/harness-bootstrap/SKILL.md`

Workflow:

1. Read the entrypoint, then load only the components needed for the current task.
2. Deliver changes through a Change Record started from `.harness/templates/change/`.
3. Run `python3 .harness/bin/harness.py validate` before delivery.

Do not edit this block by hand. Regenerate it with `python3 .harness/bin/harness.py adapt`.
<!-- END HARNESS MANAGED BLOCK -->
