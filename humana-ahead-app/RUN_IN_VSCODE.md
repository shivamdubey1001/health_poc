# Run Humana Ahead in VS Code

## 1. Open the project

Open the `humana-ahead-app` folder in VS Code.

## 2. Start the backend

Open Terminal 1:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, either use Command Prompt (`venv\Scripts\activate.bat`) or run the Python executable directly from the venv.

Verify: http://localhost:8000/api/health

API docs: http://localhost:8000/docs

## 3. Start the frontend

Open Terminal 2:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open: http://localhost:5173

## 4. Recommended demo order

1. **Overview** — show the cost-aware funnel.
2. **Ahead Queue** — compare care intent vs advocate-contact risk.
3. Open **M0001** — high-confidence knee-replacement trajectory.
4. Continue to **Readiness** — transportation is the primary opportunity.
5. Open **Outreach** — advocate approval is required.
6. Open **M0002** — facility is out of network; review database-backed alternatives.
7. Open **M0005** — explicit conservative-treatment evidence keeps care confidence below threshold and triggers one exception-based transcript lookup.
8. Open **M0006** — low care intent but high advocate-contact risk.
9. Open **Impact & Cost** — show Agent 1/Agent 2 invocation counts, token estimates and the funnel economics.

## 5. No API key needed

The default `.env.example` uses:

```env
USE_MOCK_AI=true
```

This is the safest mode for your presentation. Add a real LLM only after the UI/API behavior is stable.
