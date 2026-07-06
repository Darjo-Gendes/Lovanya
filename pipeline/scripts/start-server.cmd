@echo off
rem Detached Lovanya test-bench server (port 8000).
cd /d "%~dp0..\.."
python -m uvicorn pipeline.app.main:app --port 8000 >> "pipeline\logs\server.out" 2>&1
