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

echo Installing required libraries including python-multipart...
%PY_CMD% -m pip install python-multipart fastapi uvicorn reportlab pillow pydantic

echo Seeding database...
%PY_CMD% seed_data.py

echo Launching web server at http://127.0.0.1:8000 ...
%PY_CMD% -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

pause
