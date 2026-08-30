# Fastest Windows option

If you are on Windows, you no longer need to run the setup commands manually.

1. Extract the project ZIP.
2. Open the project folder.
3. Double-click **`start.bat`**.
4. Wait while Python and npm dependencies install.
5. When prompted, paste your OpenAI API key. The key input is hidden and is stored only in `backend/.env`.
6. The launcher validates the project, starts both servers and opens `http://127.0.0.1:5173/` automatically.

Keep the two server windows open while using the prototype. Closing them stops the application.

> `start.bat` installs the **project dependencies** automatically and will also attempt to install missing Python/Node.js runtimes via `winget`.

---

# Run Humana Ahead in VS Code

Open the **`humana-ahead-app`** folder in VS Code and use two terminals.

## 1. Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and add your OpenAI API key:

```env
USE_MOCK_AI=false
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.6-terra
```

Do **not** put the key in `frontend/.env`.

Start FastAPI:

```powershell
uvicorn app.main:app --reload --port 8000
```

Check:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

Health should show:

```json
{
  "openai_configured": true,
  "mock_ai": false
}
```

## 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the URL Vite prints, normally:

```text
http://localhost:5173
```

## 3. Demo the exact two-agent flow

1. App opens at the landing page.
2. Click **Start my assessment**.
3. On Members, check 1–5 members. Start with `M0001` and `M0002`.
4. Confirm the selected count.
5. Click **Scan for upcoming procedures**.
   - This is the first explicit OpenAI action.
6. Review Scan Results.
7. Check only the eligible members you want Agent 2 to assess.
8. Click **Run readiness assessment**.
   - This is the second explicit OpenAI action.
   - Agent 1 is not rerun.
9. Expand readiness results to inspect coverage, network, PA, referral, cost context and benefit checks.
10. Open Impact & Cost to see actual session token/cost telemetry.

## Troubleshooting

### `API key required` in the header
Confirm `backend/.env` exists and contains `OPENAI_API_KEY=...`, then restart Uvicorn.

### Scan returns `OPENAI_UNAVAILABLE`
The backend could not authenticate with or reach the OpenAI API. Read the error shown in the UI and FastAPI terminal.

### Batch limit exceeded
The prototype caps each explicit scan/readiness batch at 25 members to control API spend and latency. Select a smaller group.

### Frontend cannot reach backend
Confirm FastAPI is on port 8000 and `frontend/.env` contains:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```


## Windows pydantic-core / maturin error

The one-click launcher now requires **Python 3.12** for the backend. If an older launcher created `backend\venv` with Python 3.13 or 3.14, the new `start.bat` automatically deletes that virtual environment and recreates it with Python 3.12. This prevents `pydantic-core` from falling back to a local Rust/Maturin source build.
