# code

This folder stores reusable scripts, prototypes, and automation used across projects.

## Conventions
- Keep scripts small and composable.
- Prefer Python for data tasks; keep requirements documented.
- Put one-off experiments under `scratch/`.
- Avoid committing secrets (API keys, tokens). Use env vars.

## Structure
- Keep only project folders directly under `code/` (no generic subfolders).
- Example: `code/fred/`, `code/x_observer/`, `code/research_tools/`.
