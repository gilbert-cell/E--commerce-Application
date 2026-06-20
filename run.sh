#!/bin/bash
set -e

echo "=== SecureCommerce Setup ==="

# Backend setup
echo "[1/4] Activating virtual environment..."
source venv/bin/activate

echo "[2/4] Running migrations..."
python manage.py migrate

echo "[3/4] Creating superuser (optional - press Ctrl+C to skip)..."
python manage.py createsuperuser || true

echo "[4/4] Starting Django backend on port 8000..."
python manage.py runserver &
BACKEND_PID=$!

# Frontend setup
echo ""
echo "=== Starting React Frontend ==="
cd frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "Backend PID: $BACKEND_PID  |  Frontend PID: $FRONTEND_PID"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers."
wait
