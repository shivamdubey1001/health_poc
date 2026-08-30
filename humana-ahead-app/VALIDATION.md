# Validation notes

Validated in the build environment:

- Python modules compile successfully.
- FastAPI application starts through `TestClient` and ingests all 11 raw CSV files into SQLite.
- `/api/health`, dashboard, member context, claims, calls, settings and cost endpoints return 200.
- M0001 Care Intent returns 86% confidence and passes the threshold.
- M0001 readiness returns a transportation-support opportunity.
- M0002 readiness detects the out-of-network facility and returns three in-network database-backed alternatives.
- M0003 surfaces prior authorization as `IN_PROGRESS`.
- M0005 Care Intent remains below threshold and the readiness endpoint correctly returns HTTP 409 `CARE_INTENT_BELOW_THRESHOLD`.
- M0005 uses exception-based full transcript retrieval to validate explicit conservative-treatment counterevidence.
- M0006 remains low care-intent / high advocate-contact risk.
- Outreach approval is persisted locally and never sends a real communication.
- Session-level Agent 1 cache prevents duplicate cost logging when unchanged member evidence is re-opened.

Frontend package versions were selected as published npm versions. Package installation itself must run in a network-enabled local Node environment.
