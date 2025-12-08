@echo off
echo Starting backend server...
cd backend
uv run uvicorn main:app --workers=2 --port 50020 --host 0.0.0.0
pause