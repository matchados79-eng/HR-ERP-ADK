@echo off
:: Ignore ZKBioTime system PYTHONPATH & PYTHONHOME variables using Python -E -s flags
set PYTHONPATH=
set PYTHONHOME=

echo ===========================================================
echo  Starting Saudi HR ERP System Local Server on Windows...
echo ===========================================================

py -3 -E -s --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py -3 -E -s
) else (
    set PY_CMD=python -E -s
)

echo Checking and freeing port 8000 if occupied...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Installing required libraries...
%PY_CMD% -m pip install python-multipart fastapi uvicorn reportlab pillow pydantic httpx

echo Initializing database...
%PY_CMD% seed_data.py

echo Launching web server at http://127.0.0.1:8000 ...
%PY_CMD% -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

pause
