#!/bin/bash
# Run both backend and frontend

echo "Starting JobSync..."
echo ""

# Start backend in background
echo "Starting backend on http://localhost:8000..."
source venv/Scripts/activate
uvicorn backend.main:app --reload &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "JobSync is running!"
echo "========================================="
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
