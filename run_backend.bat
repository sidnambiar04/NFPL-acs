@echo off
echo ========================================================
echo   Starting NFPL Access Control Service Backend API
echo ========================================================
set PYTHONPATH=backend
call .\venv\Scripts\activate
uvicorn app.main:app --app-dir backend --reload --port 8000
