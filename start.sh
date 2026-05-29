#!/bin/bash
echo "========================================"
echo " Novel World Engine — 一键启动"
echo "========================================"
echo ""

cd "$(dirname "$0")/backend"

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
        echo "  Please edit .env to set your LLM_API_KEY"
        echo ""
    fi
fi

echo "  Starting server at http://localhost:5001"
echo "  Press Ctrl+C to stop"
echo ""

python -m uvicorn app.server:app --host 0.0.0.0 --port 5001
