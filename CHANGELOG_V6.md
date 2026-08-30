# Humana Ahead V6 fixes

- Fixed frontend build error `TS5096: allowImportingTsExtensions can only be used when noEmit or emitDeclarationOnly is set`.
- `frontend/tsconfig.node.json` now sets `noEmit: true`.
- Added `frontend/src/vite-env.d.ts`.
- Rebuilt `start.bat` from scratch to remove duplicated launcher blocks from the previous revision.
- Launcher still forces Python 3.12, installs dependencies, prompts securely for the OpenAI API key, validates backend/frontend, starts both services and opens the app.
