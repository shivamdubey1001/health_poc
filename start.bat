@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>&1
title Humana Ahead - Setup and Launcher
color 0A

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "DATA_DIR=%ROOT%data"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

cls
echo ===============================================================
echo                     HUMANA AHEAD
echo               One-click setup and launcher
echo ===============================================================
echo.
echo This launcher will:
echo   1. Check/install Python 3.12 and Node.js
echo   2. Create the Python virtual environment
echo   3. Install backend and frontend dependencies
echo   4. Ask for your OpenAI API key ^(input is hidden^)
echo   5. Validate the backend and frontend
echo   6. Start FastAPI and React/Vite
echo   7. Open Humana Ahead in your browser
echo.

if not exist "%BACKEND_DIR%\requirements.txt" goto :bad_location
if not exist "%BACKEND_DIR%\.env.example" goto :bad_location
if not exist "%FRONTEND_DIR%\package.json" goto :bad_location
if not exist "%FRONTEND_DIR%\tsconfig.node.json" goto :bad_location
if not exist "%DATA_DIR%" goto :bad_location

call :ensure_python_312
if errorlevel 1 goto :end_error
call :ensure_node
if errorlevel 1 goto :end_error

echo.
echo [1/6] Preparing Python 3.12 environment...
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Existing backend\venv uses a different Python version.
        echo Recreating it with Python 3.12...
        rmdir /S /Q "%VENV_DIR%"
    ) else (
        echo Existing Python 3.12 virtual environment found.
    )
)

if not exist "%VENV_PY%" (
    echo Creating backend\venv with Python 3.12...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Could not create the Python virtual environment.
        goto :end_error
    )
)

for /f "delims=" %%V in ('"%VENV_PY%" --version 2^>^&1') do echo Virtual environment: %%V

echo Updating Python packaging tools...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Could not update pip/setuptools/wheel.
    goto :end_error
)

echo Installing backend dependencies...
"%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt" --prefer-binary --disable-pip-version-check
if errorlevel 1 (
    echo First attempt failed. Retrying without the pip cache...
    "%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt" --prefer-binary --no-cache-dir --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] Backend dependency installation failed.
        goto :end_error
    )
)

echo.
echo [2/6] Installing frontend dependencies...
pushd "%FRONTEND_DIR%"
call npm install --no-audit --no-fund
if errorlevel 1 (
    popd
    echo [ERROR] Frontend dependency installation failed.
    goto :end_error
)
popd

if not exist "%FRONTEND_DIR%\.env" copy /Y "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul

echo.
echo [3/6] Configure OpenAI...
echo Your API key is stored only in backend\.env. It is never written to the frontend.
echo.
call :configure_openai
if errorlevel 1 (
    echo [ERROR] OpenAI configuration failed or was cancelled.
    goto :end_error
)

echo.
echo [4/6] Validating application code...
"%VENV_PY%" -m compileall -q "%BACKEND_DIR%\app"
if errorlevel 1 (
    echo [ERROR] Python validation failed.
    goto :end_error
)

pushd "%FRONTEND_DIR%"
call npm run build
if errorlevel 1 (
    popd
    echo [ERROR] Frontend build validation failed.
    goto :end_error
)
popd
echo Validation passed.

echo.
echo [5/6] Checking local ports...
call :check_port 8000 "FastAPI backend"
if errorlevel 1 goto :end_error
call :check_port 5173 "React frontend"
if errorlevel 1 goto :end_error

echo.
echo [6/6] Starting Humana Ahead...
start "Humana Ahead API" /D "%BACKEND_DIR%" %ComSpec% /k ""%VENV_PY%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for the backend...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 90;$i++){ try { $r=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if($r.status -eq 'ok'){$ok=$true;break} } catch {}; Start-Sleep -Seconds 1 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
    echo [ERROR] Backend did not become healthy within 90 seconds.
    echo Review the Humana Ahead API window for the underlying error.
    goto :end_error
)

start "Humana Ahead UI" /D "%FRONTEND_DIR%" %ComSpec% /k "npm run dev -- --host 127.0.0.1"

echo Waiting for the frontend...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 90;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173/' -TimeoutSec 2; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){$ok=$true;break} } catch {}; Start-Sleep -Seconds 1 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
    echo [ERROR] Frontend did not become ready within 90 seconds.
    echo Review the Humana Ahead UI window for the underlying error.
    goto :end_error
)

echo.
echo ===============================================================
echo Humana Ahead is ready.
echo Backend:     http://127.0.0.1:8000
echo API docs:    http://127.0.0.1:8000/docs
echo Application: http://127.0.0.1:5173
echo ===============================================================
echo.
start "" "http://127.0.0.1:5173/"
echo Keep the two server windows open while using the application.
echo Close those windows when you want to stop Humana Ahead.
echo.
pause
exit /b 0

:configure_openai
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$src=Join-Path $env:BACKEND_DIR '.env.example';" ^
  "$dst=Join-Path $env:BACKEND_DIR '.env';" ^
  "$secure=Read-Host 'Paste your OpenAI API key' -AsSecureString;" ^
  "$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure);" ^
  "try{$key=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)};" ^
  "if([string]::IsNullOrWhiteSpace($key)){Write-Host '[ERROR] API key cannot be empty.' -ForegroundColor Red; exit 1};" ^
  "$valid=$true; try{Invoke-RestMethod -Uri 'https://api.openai.com/v1/models' -Headers @{Authorization=('Bearer '+$key)} -Method Get -TimeoutSec 20 | Out-Null; Write-Host 'OpenAI API key accepted.' -ForegroundColor Green}catch{if($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401){Write-Host '[ERROR] OpenAI rejected this API key.' -ForegroundColor Red; $valid=$false}else{Write-Host 'Could not validate online right now. The key will still be saved.' -ForegroundColor Yellow}};" ^
  "if(-not $valid){exit 1};" ^
  "$text=Get-Content $src -Raw;" ^
  "$text=[regex]::Replace($text,'(?m)^USE_MOCK_AI=.*$','USE_MOCK_AI=false');" ^
  "$text=[regex]::Replace($text,'(?m)^LLM_PROVIDER=.*$','LLM_PROVIDER=openai');" ^
  "$text=[regex]::Replace($text,'(?m)^OPENAI_API_KEY=.*$',('OPENAI_API_KEY='+$key));" ^
  "$text=[regex]::Replace($text,'(?m)^OPENAI_MODEL=.*$','OPENAI_MODEL=gpt-5.6-terra');" ^
  "[IO.File]::WriteAllText($dst,$text,(New-Object Text.UTF8Encoding($false)));" ^
  "$key=$null; Write-Host 'OpenAI configuration saved to backend/.env.' -ForegroundColor Green"
exit /b %errorlevel%

:ensure_python_312
call :find_python_312
if not errorlevel 1 exit /b 0

echo Python 3.12 was not found. Attempting automatic installation...
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget is unavailable. Install Python 3.12 from python.org, then run start.bat again.
    exit /b 1
)
winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements --silent
if errorlevel 1 (
    echo [ERROR] Automatic Python 3.12 installation failed.
    exit /b 1
)
call :refresh_path
call :find_python_312
if errorlevel 1 (
    echo [ERROR] Python 3.12 was installed but this terminal cannot see it yet.
    echo Close this window and double-click start.bat again.
    exit /b 1
)
exit /b 0

:find_python_312
set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.12"
)
if not defined PY_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=\"%LocalAppData%\Programs\Python\Python312\python.exe\""
)
if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=python"
    )
)
if not defined PY_CMD exit /b 1
for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do echo Python: %%V
exit /b 0

:ensure_node
call :check_node
if not errorlevel 1 exit /b 0

echo Node.js LTS was not found. Attempting automatic installation...
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget is unavailable. Install current Node.js LTS, then run start.bat again.
    exit /b 1
)
winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-source-agreements --accept-package-agreements --silent
if errorlevel 1 (
    echo [ERROR] Automatic Node.js installation failed.
    exit /b 1
)
call :refresh_path
call :check_node
if errorlevel 1 (
    echo [ERROR] Node.js was installed but this terminal cannot see it yet.
    echo Close this window and double-click start.bat again.
    exit /b 1
)
exit /b 0

:check_node
where node >nul 2>&1
if errorlevel 1 exit /b 1
where npm >nul 2>&1
if errorlevel 1 exit /b 1
node -e "const [M,m]=process.versions.node.split('.').map(Number);process.exit(((M===20&&m>=19)||(M===22&&m>=12)||(M>22))?0:1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This Vite version requires Node 20.19+ or Node 22.12+.
    node --version
    exit /b 1
)
for /f "delims=" %%V in ('node --version') do echo Node.js: %%V
for /f "delims=" %%V in ('npm --version') do echo npm: %%V
exit /b 0

:refresh_path
for /f "usebackq delims=" %%P in (`powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P"
exit /b 0

:check_port
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-NetTCPConnection -State Listen -LocalPort %~1 -ErrorAction SilentlyContinue; if($p){exit 1}else{exit 0}"
if errorlevel 1 (
    echo [ERROR] Port %~1 is already in use ^(%~2^).
    echo Close the program using that port, then run start.bat again.
    exit /b 1
)
echo Port %~1 is available ^(%~2^).
exit /b 0

:bad_location
echo [ERROR] start.bat must be next to the backend, frontend, and data folders.
goto :end_error

:end_error
echo.
echo Setup did not complete. Fix the error above and run start.bat again.
echo.
pause
exit /b 1
