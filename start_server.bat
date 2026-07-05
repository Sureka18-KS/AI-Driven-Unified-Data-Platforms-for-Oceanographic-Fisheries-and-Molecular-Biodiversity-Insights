@echo off
echo ========================================================
echo Starting CORAL AI Backend API and Dashboard...
echo ========================================================
echo.
echo The server will be available at: http://localhost:8000
echo Keep this window open while you want the dashboard to work.
echo.

venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
