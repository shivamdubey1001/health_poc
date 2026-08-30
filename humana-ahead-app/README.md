# Humana Ahead — Full-stack prototype

Humana Ahead is a synthetic, internal Member Advocate prototype that demonstrates a cost-aware, two-stage AI workflow:

1. **Tier 0 activity filter** narrows the member population using cheap deterministic signals.
2. **Agent 1 — Care Intent** reviews a member's plan context, recent claims trajectory and last 5–6 Agent Assist summaries. It may request a full call transcript only when needed.
3. Members above the configurable confidence threshold (default 70%) become eligible for **Agent 2 — Readiness**.
4. **Agent 2** checks deterministic plan, provider-network and prior-authorization data, calculates a transparent readiness score and surfaces administrative friction plus in-network alternatives.
5. A **Member Advocate must approve** any outreach. Prototype mode never sends a real message.

All member/provider/plan data in this repository is synthetic.

## Stack

- Frontend: React 19, Vite, TypeScript, Tailwind CSS, React Router, Recharts, Lucide React
- Backend: Python, FastAPI, SQLAlchemy, SQLite, Pandas, Pydantic
- AI: mock mode by default; optional OpenAI Responses API adapter

## Project structure

```text
humana-ahead-app/
├── frontend/
├── backend/
├── data/
└── README.md
```

## Quick start

### 1) Backend

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

On first startup the backend ingests the CSV files from `../data` into `backend/humana_ahead.db`.

API docs: http://localhost:8000/docs

### 2) Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env        # Windows: copy .env.example .env
npm run dev
```

Open: http://localhost:5173

## Demo members

- `M0001` — high-confidence knee-replacement trajectory; mostly ready with a transportation-support opportunity.
- `M0002` — high-confidence knee-replacement trajectory; likely facility out of network and no matching knee PA record.
- `M0003` — likely hip replacement; pending authorization.
- `M0004` — likely cataract surgery.
- `M0005` — orthopedic history but explicit conservative-treatment language; low care-intent confidence.
- `M0006` — low surgery confidence but high predicted advocate-contact risk from repeated unresolved billing contacts.

## Mock AI mode

The default configuration is:

```env
USE_MOCK_AI=true
```

Mock mode runs fully offline. It uses deterministic heuristics plus fixed synthetic demo outputs for the six showcase members. The API schemas are identical to real-model mode.

## Optional OpenAI mode

The backend includes an adapter for the OpenAI Responses API. The official API exposes `POST /v1/responses` and returns usage fields that can be used for token/cost tracking.

Set:

```env
USE_MOCK_AI=false
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5.6-sol
```

No API key is committed to the repository.

The real-model path intentionally sends only a compact member evidence packet. Full transcripts remain behind the `GET /api/calls/{call_id}/transcript` tool and are not automatically included.

## Key APIs

```text
GET  /api/health
GET  /api/dashboard/overview
GET  /api/members
GET  /api/members/{member_id}
GET  /api/members/{member_id}/context
GET  /api/members/{member_id}/claims
GET  /api/members/{member_id}/calls
GET  /api/calls/{call_id}/transcript
POST /api/members/{member_id}/care-intent
POST /api/members/{member_id}/readiness
GET  /api/members/{member_id}/provider-alternatives
POST /api/members/{member_id}/outreach/draft
POST /api/members/{member_id}/outreach/approve
POST /api/members/{member_id}/outreach/reject
GET  /api/analytics/cost
GET  /api/queue/ahead
GET  /api/settings
PUT  /api/settings
```

## Data design

The CSV source files stay raw and contain **no** prediction/readiness labels. SQLite is only the local query layer. Predictions, readiness scores and outreach recommendations are application outputs.

### Agent 1 inputs

- member enrollment
- plan master
- claims history (12-month default lookback)
- last six Agent Assist summaries
- transcript IDs, not transcript text

### Agent 2 inputs

Only after Agent 1 crosses the threshold:

- plan benefits
- benefit accumulators
- provider directory
- provider network
- prior authorizations

## Cost controls represented in the prototype

- Event/activity funnel before LLM evaluation
- Agent 2 only after confidence threshold
- Summaries before full transcripts
- Per-agent usage logging
- Session-level caching so unchanged member evidence is not reprocessed on every screen navigation
- Estimated cost per evaluation and per high-confidence member
- Settings for threshold, lookback and transcript fallback

Pricing values in `.env.example` are **prototype assumptions**, not vendor quotes.

## Responsible AI constraints

- Administrative support only; no diagnosis or treatment recommendation.
- Care Intent score is called a **confidence score**, not a calibrated clinical probability.
- Low-confidence cases remain in monitor state.
- No real outbound communication occurs.
- Human approval is required for outreach.
- The UI shows evidence summaries, not hidden chain-of-thought.
- Provider alternatives come from the synthetic provider/network database only.

## Known prototype limitations

- ZIP3 proximity is used for provider-alternative ranking; it is not true driving distance.
- Mock AI outputs are deterministic demonstrations, not trained predictions.
- The optional real-model adapter has not been enabled by default because the take-home should remain demoable without external credentials.
- SQLite is appropriate for local prototyping, not payer production scale.
