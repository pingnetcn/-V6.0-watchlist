@echo off
if not exist .venv\Scripts\python.exe (
    echo .venv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)
echo Verifying port 8905 alive (main app must stay alive)...
powershell -Command "(Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://127.0.0.1:8905/ -ErrorAction SilentlyContinue).StatusCode"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8910" ^| findstr LISTENING') do taskkill /F /PID %%p 2>nul
cd /d "%~dp0"
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
if exist lib\__pycache__ rmdir /s /q lib\__pycache__ 2>nul
if exist components\__pycache__ rmdir /s /q components\__pycache__ 2>nul
if exist pages\__pycache__ rmdir /s /q pages\__pycache__ 2>nul
start /b "" .venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8910 --server.headless true
timeout /t 8 /nobreak >nul
echo HTTP check:
curl -s -o /dev/null -w "  8910 = %%{http_code}\n" http://127.0.0.1:8910/
curl -s -o /dev/null -w "  8905 = %%{http_code}\n" http://127.0.0.1:8905/