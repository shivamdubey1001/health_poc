@echo off
setlocal EnableExtensions

title Humana Ahead - One Click Start

REM Put this file directly inside the humana-ahead-app folder.
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV_PY=%BACKEND%\venv\Scripts\python.exe"

echo.
echo ============================================================
echo                 HUMANA AHEAD - START
 echo ============================================================
echo.

if not exist "%BACKEND%\app\main.py" (
 echo ERROR: backend\app\main.py not found.
 echo Put start.bat inside the humana-ahead-app folder.
 pause
 exit /b 1
)
if not exist "%FRONTEND%\package.json" (
 echo ERROR: frontend\package.json not found.
 pause
 exit /b 1
)

set "PYTHON_CMD="
if exist "C:\Python314\python.exe" set "PYTHON_CMD=C:\Python314\python.exe"
if not defined PYTHON_CMD (
 where py >nul 2>nul
 if not errorlevel 1 (
  py -3.14 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3.14"
 )
)
if not defined PYTHON_CMD (
 where python >nul 2>nul
 if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
 echo ERROR: Python 3.14 was not found.
 pause
 exit /b 1
)

echo Python:
%PYTHON_CMD% --version

echo.
echo [1/4] Preparing Python environment...
if not exist "%VENV_PY%" (
 %PYTHON_CMD% -m venv "%BACKEND%\venv"
 if errorlevel 1 goto :fail
)

"%VENV_PY%" -c "import fastapi,pydantic,pydantic_core,pydantic_settings,sqlalchemy,pandas,httpx" >nul 2>nul
if errorlevel 1 (
 echo Installing backend requirements...
 "%VENV_PY%" -m pip install --upgrade pip setuptools wheel
 if errorlevel 1 goto :fail
 "%VENV_PY%" -m pip install -r "%BACKEND%\requirements.txt"
 if errorlevel 1 goto :fail
) else echo [OK] Backend dependencies ready.

echo.
echo [2/4] Preparing configuration...
if not exist "%BACKEND%\.env" (
 if exist "%BACKEND%\.env.example" (
  copy /Y "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
 ) else (
  >"%BACKEND%\.env" echo USE_MOCK_AI=true
 )
 echo [OK] Created backend\.env. Mock AI is enabled by default.
) else echo [OK] backend\.env already exists.

echo.
echo [3/4] Preparing frontend...
where npm >nul 2>nul
if errorlevel 1 (
 echo ERROR: npm was not found. Install Node.js LTS and run start.bat again.
 echo https://nodejs.org/
 pause
 exit /b 1
)
if not exist "%FRONTEND%\node_modules" (
 cd /d "%FRONTEND%"
 call npm install
 if errorlevel 1 goto :fail
 cd /d "%ROOT%"
) else echo [OK] Frontend dependencies ready.

echo.
echo [4/4] Starting application...
start "Humana Ahead - Backend" cmd /k "cd /d "%BACKEND%" && "%VENV_PY%" -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Humana Ahead - Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ============================================================
echo                 HUMANA AHEAD STARTED
 echo ============================================================
echo Backend:  http://127.0.0.1:8000
 echo API Docs: http://127.0.0.1:8000/docs
 echo Frontend: http://localhost:5173
 echo.
echo Mock AI is enabled by default - no API key required.
echo To stop: close the Backend and Frontend terminal windows.
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo SETUP FAILED - see the error above.
echo ============================================================
pause
exit /b 1
