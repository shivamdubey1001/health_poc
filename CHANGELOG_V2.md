# V2 workflow changes

- Added screenshot-inspired landing page and Humana-like green/cream visual system.
- Landing page is now `/`; Overview moved to `/overview`.
- Added collapsible field guide to Members.
- Added member-selection checkboxes and selected count.
- Added explicit batch Agent 1 endpoint and Scan Results screen.
- Added independent readiness-selection checkboxes.
- Added explicit batch Agent 2 endpoint and Readiness Results screen.
- Removed all automatic Agent 1 / Agent 2 invocation from page loads, queue generation and outreach drafting.
- Changed default AI mode from mock to real OpenAI Responses API.
- OpenAI API key remains backend-only.
- Agent 2 now performs deterministic readiness checks plus a real OpenAI prioritization call.
- Removed hard-coded ROI/call-savings values from Impact & Cost.
- Added measured token/cost telemetry only.
