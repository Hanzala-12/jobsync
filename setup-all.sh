#!/bin/bash
# Complete setup script for JobSync (Backend + Frontend)

echo "========================================="
echo "JobSync Setup"
echo "========================================="
echo ""

# Backend Setup
echo "Setting up backend..."
echo ""

# Create virtual environment
python -m venv venv

echo "Virtual environment created."
echo ""

# Install backend dependencies
echo "Installing backend dependencies..."
./venv/Scripts/pip install -r backend/requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    cp backend/.env.example .env
    echo "Created .env file. Please edit it and add your GROQ_API_KEY"
fi

echo ""
echo "Backend setup complete!"
echo ""

# Frontend Setup
echo "Setting up frontend..."
echo ""

cd frontend

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
npm install

# Copy frontend environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created frontend .env file"
fi

cd ..

echo ""
echo "Frontend setup complete!"
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GROQ_API_KEY from https://console.groq.com"
echo ""
echo "2. Start the backend (in one terminal):"
echo "   source venv/Scripts/activate  # Windows"
echo "   bash run.sh"
echo ""
echo "3. Start the frontend (in another terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
