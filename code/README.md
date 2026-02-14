# code

This folder stores reusable scripts, prototypes, and automation used across projects.

## Conventions
- Keep scripts small and composable.
- Prefer Python for data tasks; keep requirements documented.
- Put one-off experiments under `scratch/`.
- Avoid committing secrets (API keys, tokens). Use env vars.

## Suggested structure
- `scripts/` – reusable scripts
- `pipelines/` – multi-step workflows
- `notebooks/` – optional
- `scratch/` – temporary experiments
