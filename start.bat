@echo off
chcp 65001 >nul
echo ========================================
echo  Novel World Engine — 一键启动
echo ========================================
echo.

cd /d "%~dp0backend"

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo   Created .env from .env.example
        echo   Please edit .env to set your LLM_API_KEY
        echo.
    )
)

echo   Starting server at http://localhost:5001
echo   Press Ctrl+C to stop
echo.

python -m uvicorn app.server:app --host 0.0.0.0 --port 5001
pause
