# Humana Ahead — OpenAI Full-Stack Prototype

Humana Ahead is a synthetic internal Member Advocate prototype that lets a human select members, explicitly run an OpenAI-based **Care Intent Agent (Agent 1)** and then explicitly choose which eligible members should receive an **Administrative Readiness assessment (Agent 2)**.

## One-click Windows startup

For Windows, the easiest way to run the full prototype is to double-click `start.bat` in the project root. The launcher checks Python and Node.js and, when they are missing, attempts to install Python 3.12 and Node.js LTS through Windows Package Manager (`winget`). It then creates `backend\venv`, installs all Python and npm dependencies, asks for the OpenAI API key with hidden input, writes it only to `backend/.env`, validates the backend/frontend code, starts FastAPI on port 8000 and Vite on port 5173, waits until both are healthy, then opens the landing page automatically.

If Python or Node.js is missing, `start.bat` first attempts a one-time `winget` installation. If `winget` is unavailable or Windows needs a fresh terminal after installing a runtime, the launcher gives the exact next step instead of partially starting the application.

The API key is never written to the React frontend. `backend/.env` is excluded by `.gitignore`.

## Important behavior

The app is deliberately **not** an always-on agent swarm.

1. `/` is a public-style landing page. Loading it makes **no OpenAI call**.
2. **Start my assessment** opens the Members page.
3. The Members page loads all 250 synthetic members and shows raw/recent payer metrics. Loading/searching/selecting makes **no OpenAI call**.
4. The advocate checks specific members and clicks **Scan for upcoming procedures**.
   - Frontend call: `POST /api/assessments/care-intent`
   - Backend: one Agent 1 OpenAI Responses API assessment per selected member.
   - Agent 1 sees member/plan context, historical claims and the latest Agent Assist summaries. It does **not** receive provider-network or prior-authorization tables.
5. Scan Results shows only those explicitly selected members.
6. Eligible members can then be checked independently for readiness. Clicking **Run readiness assessment** is required.
   - Frontend call: `POST /api/assessments/readiness`
   - Agent 1 is **not rerun**.
   - Backend performs deterministic coverage/network/PA/referral/cost/benefit lookups, calculates a transparent readiness score and calls OpenAI Agent 2 only to prioritize the unresolved administrative action.
7. Readiness Results shows only members explicitly selected for Agent 2.
8. Outreach is always human-reviewed and simulated. No real member communication is sent.

## OpenAI configuration

The OpenAI API key stays on the FastAPI server. It is never placed in React/Vite environment variables and never sent to the browser.

```bash
cd backend
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `backend/.env`:

```env
USE_MOCK_AI=false
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6-terra
```

The prototype uses the OpenAI **Responses API** at `POST https://api.openai.com/v1/responses`.

## Frontend flow

### Landing page
- Humana Ahead introduction
- raw dataset snapshot
- OpenAI configuration status
- Start my assessment button

### Members
- collapsible field guide
- all 250 members
- checkbox selection
- claims 90d / 180d
- calls 90d
- last call topic
- authorization count 180d
- latest activity
- selected-member count
- explicit Agent 1 scan button

### Scan Results
- one row per selected member
- predicted upcoming care event
- Care Intent Confidence
- estimated timing
- Advocate Contact Risk
- expandable evidence
- readiness eligibility
- second independent checkbox selection
- explicit Agent 2 button

### Readiness Results
- readiness score
- checklist
- score deductions
- top issue
- OpenAI-prioritized next administrative action
- database-backed in-network alternatives where applicable

### Impact & Cost
Only measured prototype API usage is shown:
- Agent 1 calls
- Agent 2 calls
- input/output tokens
- transcript fallbacks
- estimated inference spend
- latency

The prototype intentionally does **not** invent labor savings, call deflection or ROI.

## Raw data

The `data/` directory contains only synthetic source/reference data:

- `member_enrollment.csv`
- `plan_master.csv`
- `plan_benefits.csv`
- `benefit_accumulators.csv`
- `claims_history.csv`
- `member_advocate_calls.csv`
- `call_transcripts.csv`
- `agent_assist_call_summaries.csv`
- `provider_directory.csv`
- `provider_network.csv`
- `prior_authorizations.csv`

Prediction/readiness labels are not stored in the input CSVs.

## Backend

```text
FastAPI
SQLite / SQLAlchemy
OpenAI Responses API
Pydantic
```

Key endpoints:

```text
GET  /api/landing/summary
GET  /api/members
POST /api/assessments/care-intent      # explicit Agent 1 batch
POST /api/assessments/readiness        # explicit Agent 2 batch
GET  /api/members/{id}/care-intent/latest
GET  /api/members/{id}/readiness/latest
GET  /api/analytics/cost
```

A batch is capped at 25 selected members in the prototype to make accidental API spend and latency visible/manageable.

## Responsible AI boundaries

- Care Intent Confidence is not a calibrated clinical probability.
- The system does not diagnose or recommend treatment.
- Agent 1 has no access to PA/provider-network tables, avoiding obvious future-event leakage.
- Agent 2 cannot change deterministic readiness facts or the readiness score.
- Provider alternatives must come from provider/network tables.
- Full transcripts are exception-based: Agent 1 can request one recent transcript when an Agent Assist summary is materially ambiguous.
- Human approval is required before simulated outreach.

See `RUN_IN_VSCODE.md` for exact startup steps and `VALIDATION.md` for validation performed in the build environment.
