# Validation

Validation performed after the workflow/UI refactor.

## Backend

- Python `compileall`: **PASS**
- SQLite initialization from all raw CSVs: **PASS**
- Landing summary: **PASS**
  - 250 members
  - 762 claim lines in the 180-day window
  - 450 advocate calls in the 90-day window
  - 85 authorization records
- Member metrics endpoint across 250 members: **PASS**
- Opening landing/overview/members/queue with no API key creates no model call: **PASS**
- Agent 1 without API key returns a clear configuration error: **PASS**
- Readiness before Agent 1 is skipped/blocked rather than silently invoking Agent 1: **PASS**

## Two-call separation test

The OpenAI provider was replaced locally with a deterministic test double solely to validate orchestration without spending an API call.

For `M0002`:

1. `POST /api/assessments/care-intent`
   - exactly one Agent 1 provider call
2. `POST /api/assessments/readiness`
   - exactly one Agent 2 provider call
   - **no second Agent 1 call**
3. Readiness correctly resolved the synthetic surgeon from call/claim evidence.
4. The facility named in Agent Assist history resolved to an out-of-network facility.
5. The system returned 3 in-network alternatives from the synthetic provider/network database.

Result: **PASS**

## Frontend

- All project TypeScript/TSX source files (except the declaration-only Vite env file) were syntax-transpiled with TypeScript: **PASS**
- `npm install` could not be completed in the build sandbox because registry access timed out. Run `npm install` locally in VS Code before `npm run dev`.

## UX/workflow checks

- `/` is landing page, not Overview: **PASS**
- Start my assessment → Members: **PASS**
- Member field guide can be hidden: **PASS**
- Per-member checkboxes: **PASS**
- Selected-member count shown before Agent 1: **PASS**
- Agent 1 batch uses only checked members: **PASS**
- Scan Results does not trigger readiness: **PASS**
- Independent readiness checkboxes: **PASS**
- Agent 2 uses only explicitly selected eligible members: **PASS**
- Individual Intelligence/Readiness detail pages load cached results only and do not automatically rerun agents: **PASS**
- Outreach draft does not automatically invoke Agent 1 or Agent 2: **PASS**


## V6 fixes
- Fixed `tsconfig.node.json` TS5096 by enabling `noEmit: true`.
- Added `src/vite-env.d.ts` for `import.meta.env` typing.
- Replaced the launcher with a clean self-contained Windows batch file.
